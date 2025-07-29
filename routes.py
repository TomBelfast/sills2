from flask import (
    render_template, request, jsonify, redirect, url_for, 
    flash, abort, session, send_from_directory
)
from werkzeug.utils import secure_filename
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import desc, asc
from extensions import db, limiter
from models import Client, Sill, Settings, MaterialPrices, DefaultSettings
from utils import (
    validate_uk_postcode, validate_phone, validate_email,
    calculate_materials, calculate_cutting_layout
)
from contract_parser import ContractParser
import logging
import os
import math
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

def register_routes(app):
    @app.route('/')
    def index():
        try:
            page = request.args.get('page', 1, type=int)
            per_page = 10
            
            try:
                db.session.execute(db.text("SELECT 1"))
                logger.info("Database connection OK")
                
                clients = Client.query.order_by(Client.id.desc()).paginate(page=page, per_page=per_page)
                logger.info(f"Found {clients.total if clients else 0} clients")
                
                return render_template('index.html', clients=clients.items, pagination=clients)
            except Exception as db_error:
                logger.error(f"Database error: {str(db_error)}")
                flash('Database connection error', 'danger')
                return render_template('error.html', 
                                    error="Database connection error",
                                    error_type="Database Error",
                                    error_details=str(db_error)), 500
        except Exception as e:
            logger.error(f'Error in index route: {str(e)}')
            return render_template('error.html', 
                                error="Internal server error",
                                error_type=type(e).__name__,
                                error_details=str(e)), 500

    @app.route('/clients')
    @limiter.limit("20/minute")
    def clients():
        try:
            active_client_id = session.get('active_client_id')
            active_client = Client.query.get(active_client_id) if active_client_id else None
            
            clients = Client.query.order_by(asc(Client.last_name), asc(Client.first_name)).all()
            return render_template('clients.html', 
                                clients=clients, 
                                active_client=active_client)
        except Exception as e:
            logger.error(f"Error in clients route: {str(e)}")
            flash(f'Error loading clients: {str(e)}', 'error')
            return redirect(url_for('index'))

    @app.route('/sills', methods=['GET', 'POST'])
    @limiter.limit("20/minute")
    def sills():
        try:
            active_client_id = session.get('active_client_id')
            active_client = Client.query.get(active_client_id) if active_client_id else None
            
            if request.method == 'POST':
                try:
                    client_id = request.form.get('client_id')
                    length_str = request.form.get('length')
                    depth_str = request.form.get('depth')
                    high_str = request.form.get('high')
                    angle_str = request.form.get('angle')
                    
                    if not length_str or not depth_str:
                        raise ValueError("Length and depth are required")
                    
                    length = float(length_str)
                    depth = float(depth_str)
                    high = float(high_str) if high_str and high_str.strip() else None
                    angle = float(angle_str) if angle_str and angle_str.strip() else None
                    color = request.form.get('color')
                    sill_type = request.form.get('sill_type')
                    location = request.form.get('location')
                    has_95mm = 'has_95mm' in request.form

                    if not all([client_id, color, sill_type, location]):
                        if request.is_json or request.headers.get('Content-Type') == 'application/x-www-form-urlencoded':
                            return jsonify({'status': 'error', 'message': 'All fields are required!'})
                        flash('All fields are required!', 'error')
                        return redirect(url_for('sills'))

                    if not client_id:
                        raise ValueError("Client ID is required")

                    new_sill = Sill()
                    new_sill.client_id = int(client_id)
                    new_sill.order_number = Sill.generate_order_number()
                    new_sill.length = length
                    new_sill.depth = depth
                    new_sill.high = high
                    new_sill.angle = angle
                    new_sill.color = color or ""
                    new_sill.sill_type = sill_type or ""
                    new_sill.location = location or ""
                    new_sill.has_95mm = has_95mm
                    
                    db.session.add(new_sill)
                    db.session.commit()

                    session['last_client_id'] = client_id
                    session['last_color'] = color
                    session['last_sill_type'] = sill_type

                    # Check if it's an AJAX request
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
                        return jsonify({'status': 'success', 'message': 'Window sill added successfully!'})
                    
                    flash('Window sill added successfully!', 'success')
                    return redirect(url_for('sills'))
                except Exception as e:
                    db.session.rollback()
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
                        return jsonify({'status': 'error', 'message': f'Error adding window sill: {str(e)}'})
                    flash(f'Error adding window sill: {str(e)}', 'error')
                    return redirect(url_for('sills'))

            if not active_client:
                flash('Please select a client first', 'warning')
                return redirect(url_for('clients'))
            
            sills = Sill.query.filter_by(client_id=active_client_id).all()
            clients = Client.query.order_by(asc(Client.last_name), asc(Client.first_name)).all()
            
            return render_template('sills.html', 
                                sills=sills, 
                                client=active_client,
                                active_client=active_client,
                                clients=clients,
                                colors=app.config['COLORS'],
                                sill_types=app.config['SILL_TYPES'])
        except Exception as e:
            logger.error(f"Error in sills route: {str(e)}")
            return render_template('error.html', error=str(e)), 500

    @app.route('/materials')
    @limiter.limit("20/minute")
    def materials():
        active_client_id = session.get('active_client_id')
        if not active_client_id:
            flash('Please select a client first', 'warning')
            return redirect(url_for('clients'))

        active_client = Client.query.get_or_404(active_client_id)
        sills = Sill.query.filter_by(client_id=active_client_id).all()
        
        settings = Settings.query.first()
        if not settings:
            flash('Settings not found', 'error')
            return redirect(url_for('settings'))
        
        all_materials = calculate_materials_for_sills(sills, settings)
        cutting_layouts = calculate_cutting_layout(sills)

        return render_template('materials.html', 
                            sills=sills, 
                            client=active_client,
                            materials=all_materials,
                            cutting_layouts=cutting_layouts)

    @app.route('/price')
    @limiter.limit("20/minute")
    def price():
        active_client_id = session.get('active_client_id')
        if not active_client_id:
            flash('Please select a client first', 'warning')
            return redirect(url_for('clients'))

        active_client = Client.query.get_or_404(active_client_id)
        sills = Sill.query.filter_by(client_id=active_client_id).all()
        prices = MaterialPrices.query.first()

        if not prices:
            flash('Material prices not found', 'error')
            return redirect(url_for('settings'))

        sills_with_costs = calculate_costs_for_sills(sills, prices)
        total_material_cost = sum(s['material_cost'] for s in sills_with_costs)
        total_fitting_cost = sum(s['fitting_cost'] for s in sills_with_costs)
        total_cost = total_material_cost + total_fitting_cost

        return render_template('price.html', 
                            sills=sills_with_costs, 
                            client=active_client,
                            total_material_cost=total_material_cost,
                            total_fitting_cost=total_fitting_cost,
                            total_cost=total_cost)

    @app.route('/settings', methods=['GET'])
    @limiter.limit("20/minute")
    def settings():
        settings = Settings.query.first()
        prices = MaterialPrices.query.first()
        logger.info(f"Current settings: {settings.__dict__ if settings else 'No settings found'}")
        logger.info(f"Current prices: {prices.__dict__ if prices else 'No prices found'}")
        return render_template('settings.html', settings=settings, prices=prices)

    @app.route('/update_settings', methods=['POST'])
    @limiter.limit("20/minute")
    def update_settings():
        logger.info("update_settings function called")
        try:
            # Log form data
            logger.info(f"Received form data: {dict(request.form)}")
            
            # Get form data
            settings = Settings.query.first()
            prices = MaterialPrices.query.first()
            
            if not settings:
                settings = Settings()
                db.session.add(settings)
            
            if not prices:
                prices = MaterialPrices()
                db.session.add(prices)
            
            # Update settings with detailed logging
            new_cutting_allowance = float(request.form.get('cutting_allowance', settings.cutting_allowance))
            logger.info(f"Current cutting_allowance: {settings.cutting_allowance}")
            logger.info(f"New cutting_allowance from form: {new_cutting_allowance}")
            
            settings.plate_length = float(request.form.get('plate_length', settings.plate_length))
            settings.length_95mm = float(request.form.get('length_95mm', settings.length_95mm))
            settings.cutting_allowance = new_cutting_allowance
            settings.hot_glue_per_meter = float(request.form.get('hot_glue_per_meter', settings.hot_glue_per_meter))
            settings.glue_with_activator_per_meter = float(request.form.get('glue_with_activator_per_meter', settings.glue_with_activator_per_meter))
            settings.silicone_per_meter = float(request.form.get('silicone_per_meter', settings.silicone_per_meter))
            settings.silicone_color_per_meter = float(request.form.get('silicone_color_per_meter', settings.silicone_color_per_meter))
            settings.pvc_cleaner_per_meter = float(request.form.get('pvc_cleaner_per_meter', settings.pvc_cleaner_per_meter))
            settings.fixall_per_meter = float(request.form.get('fixall_per_meter', settings.fixall_per_meter))
            settings.glue_color_extra = float(request.form.get('glue_color_extra', settings.glue_color_extra))
            
            # Update prices
            prices.gp_board_price = float(request.form.get('gp_board_price', prices.gp_board_price))
            prices.capit_board_price = float(request.form.get('capit_board_price', prices.capit_board_price))
            prices.board_95mm_price = float(request.form.get('board_95mm_price', prices.board_95mm_price))
            prices.glue_price = float(request.form.get('glue_price', prices.glue_price))
            prices.hot_glue_price = float(request.form.get('hot_glue_price', prices.hot_glue_price))
            prices.silicone_price = float(request.form.get('silicone_price', prices.silicone_price))
            prices.silicone_color_price = float(request.form.get('silicone_color_price', prices.silicone_color_price))
            prices.pvc_cleaner_price = float(request.form.get('pvc_cleaner_price', prices.pvc_cleaner_price))
            prices.s2_clear_silicone_price = float(request.form.get('s2_clear_silicone_price', prices.s2_clear_silicone_price))
            prices.fixall_white_price = float(request.form.get('fixall_white_price', prices.fixall_white_price))
            prices.glue_with_activator_price = float(request.form.get('glue_with_activator_price', prices.glue_with_activator_price))
            prices.fitting_price_straight = float(request.form.get('fitting_price_straight', prices.fitting_price_straight))
            prices.fitting_price_c_shape = float(request.form.get('fitting_price_c_shape', prices.fitting_price_c_shape))
            prices.fitting_price_bay_curve = float(request.form.get('fitting_price_bay_curve', prices.fitting_price_bay_curve))
            prices.fitting_price_conservatory = float(request.form.get('fitting_price_conservatory', prices.fitting_price_conservatory))
            prices.fitting_price_95mm = float(request.form.get('fitting_price_95mm', prices.fitting_price_95mm))
            
            db.session.commit()
            logger.info(f"Settings committed to database. New cutting_allowance: {settings.cutting_allowance}")
            
            # Check if it's an AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
                return jsonify({'status': 'success', 'message': 'Settings updated successfully!'})
            
            flash('Settings updated successfully!', 'success')
            return redirect(url_for('settings'))
            
        except Exception as e:
            db.session.rollback()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
                return jsonify({'status': 'error', 'message': f'Error updating settings: {str(e)}'})
            flash(f'Error updating settings: {str(e)}', 'error')
            return redirect(url_for('settings'))

    @app.route('/reset_settings', methods=['POST'])
    @limiter.limit("20/minute")
    def reset_settings():
        logger.info("reset_settings function called")
        try:
            # Reset to default values
            settings = Settings.query.first()
            prices = MaterialPrices.query.first()
            
            logger.info(f"Before reset - Current settings cutting_allowance: {settings.cutting_allowance if settings else 'None'}")
            
            if settings:
                logger.info("Deleting current settings")
                db.session.delete(settings)
            if prices:
                logger.info("Deleting current prices")
                db.session.delete(prices)
            
            # Get saved default settings or create new ones
            default_settings = DefaultSettings.query.first()
            
            if default_settings:
                logger.info(f"Using saved default settings with cutting_allowance: {default_settings.cutting_allowance}")
                # Use saved default settings
                new_settings = Settings()
                new_settings.plate_length = default_settings.plate_length
                new_settings.length_95mm = default_settings.length_95mm
                new_settings.cutting_allowance = default_settings.cutting_allowance
                new_settings.hot_glue_per_meter = default_settings.hot_glue_per_meter
                new_settings.glue_with_activator_per_meter = default_settings.glue_with_activator_per_meter
                new_settings.silicone_per_meter = default_settings.silicone_per_meter
                new_settings.silicone_color_per_meter = default_settings.silicone_color_per_meter
                new_settings.pvc_cleaner_per_meter = default_settings.pvc_cleaner_per_meter
                new_settings.fixall_per_meter = default_settings.fixall_per_meter
                new_settings.glue_color_extra = default_settings.glue_color_extra
            else:
                logger.info("No saved defaults found, using built-in defaults")
                # Use built-in default settings
                new_settings = Settings()
            
            new_prices = MaterialPrices()
            
            logger.info(f"Creating new settings with cutting_allowance: {new_settings.cutting_allowance}")
            db.session.add(new_settings)
            db.session.add(new_prices)
            db.session.commit()
            logger.info("Settings reset completed successfully")
            
            flash('Settings reset to default values!', 'success')
            return redirect(url_for('settings'))
            
        except Exception as e:
            logger.error(f"Error in reset_settings: {str(e)}")
            db.session.rollback()
            flash(f'Error resetting settings: {str(e)}', 'error')
            return redirect(url_for('settings'))

    @app.route('/reset_to_builtin', methods=['POST'])
    @limiter.limit("20/minute")
    def reset_to_builtin():
        logger.info("reset_to_builtin function called")
        try:
            # Reset to built-in default values (ignore saved defaults)
            settings = Settings.query.first()
            prices = MaterialPrices.query.first()
            
            logger.info(f"Before builtin reset - Current settings cutting_allowance: {settings.cutting_allowance if settings else 'None'}")
            
            if settings:
                logger.info("Deleting current settings")
                db.session.delete(settings)
            if prices:
                logger.info("Deleting current prices")
                db.session.delete(prices)
            
            # Use built-in default settings (ignore DefaultSettings table)
            logger.info("Using built-in default settings")
            new_settings = Settings()
            new_prices = MaterialPrices()
            
            logger.info(f"Creating new settings with built-in cutting_allowance: {new_settings.cutting_allowance}")
            db.session.add(new_settings)
            db.session.add(new_prices)
            db.session.commit()
            logger.info("Built-in settings reset completed successfully")
            
            flash('Settings reset to built-in default values!', 'success')
            return redirect(url_for('settings'))
            
        except Exception as e:
            logger.error(f"Error in reset_to_builtin: {str(e)}")
            db.session.rollback()
            flash(f'Error resetting to built-in settings: {str(e)}', 'error')
            return redirect(url_for('settings'))

    @app.route('/save_as_default', methods=['POST'])
    @limiter.limit("20/minute")
    def save_as_default():
        logger.info("save_as_default function called")
        try:
            # First, update current settings with form data, then save as default
            settings = Settings.query.first()
            prices = MaterialPrices.query.first()
            
            if not settings:
                settings = Settings()
                db.session.add(settings)
            
            if not prices:
                prices = MaterialPrices()
                db.session.add(prices)
            
            # Update settings with form data
            new_cutting_allowance = float(request.form.get('cutting_allowance', settings.cutting_allowance))
            logger.info(f"Form data cutting_allowance: {new_cutting_allowance}")
            
            settings.plate_length = float(request.form.get('plate_length', settings.plate_length))
            settings.length_95mm = float(request.form.get('length_95mm', settings.length_95mm))
            settings.cutting_allowance = new_cutting_allowance
            settings.hot_glue_per_meter = float(request.form.get('hot_glue_per_meter', settings.hot_glue_per_meter))
            settings.glue_with_activator_per_meter = float(request.form.get('glue_with_activator_per_meter', settings.glue_with_activator_per_meter))
            settings.silicone_per_meter = float(request.form.get('silicone_per_meter', settings.silicone_per_meter))
            settings.silicone_color_per_meter = float(request.form.get('silicone_color_per_meter', settings.silicone_color_per_meter))
            settings.pvc_cleaner_per_meter = float(request.form.get('pvc_cleaner_per_meter', settings.pvc_cleaner_per_meter))
            settings.fixall_per_meter = float(request.form.get('fixall_per_meter', settings.fixall_per_meter))
            settings.glue_color_extra = float(request.form.get('glue_color_extra', settings.glue_color_extra))
            
            # Update prices with form data
            prices.gp_board_price = float(request.form.get('gp_board_price', prices.gp_board_price))
            prices.capit_board_price = float(request.form.get('capit_board_price', prices.capit_board_price))
            prices.board_95mm_price = float(request.form.get('board_95mm_price', prices.board_95mm_price))
            prices.glue_price = float(request.form.get('glue_price', prices.glue_price))
            prices.hot_glue_price = float(request.form.get('hot_glue_price', prices.hot_glue_price))
            prices.silicone_price = float(request.form.get('silicone_price', prices.silicone_price))
            prices.silicone_color_price = float(request.form.get('silicone_color_price', prices.silicone_color_price))
            prices.pvc_cleaner_price = float(request.form.get('pvc_cleaner_price', prices.pvc_cleaner_price))
            prices.s2_clear_silicone_price = float(request.form.get('s2_clear_silicone_price', prices.s2_clear_silicone_price))
            prices.fixall_white_price = float(request.form.get('fixall_white_price', prices.fixall_white_price))
            prices.glue_with_activator_price = float(request.form.get('glue_with_activator_price', prices.glue_with_activator_price))
            prices.fitting_price_straight = float(request.form.get('fitting_price_straight', prices.fitting_price_straight))
            prices.fitting_price_c_shape = float(request.form.get('fitting_price_c_shape', prices.fitting_price_c_shape))
            prices.fitting_price_bay_curve = float(request.form.get('fitting_price_bay_curve', prices.fitting_price_bay_curve))
            prices.fitting_price_conservatory = float(request.form.get('fitting_price_conservatory', prices.fitting_price_conservatory))
            prices.fitting_price_95mm = float(request.form.get('fitting_price_95mm', prices.fitting_price_95mm))
            
            logger.info(f"Updated settings with cutting_allowance: {settings.cutting_allowance}")
            
            # Now save as default
            default_settings = DefaultSettings.query.first()
            if not default_settings:
                default_settings = DefaultSettings()
                db.session.add(default_settings)
            
            # Copy updated settings to default
            default_settings.plate_length = settings.plate_length
            default_settings.length_95mm = settings.length_95mm
            default_settings.cutting_allowance = settings.cutting_allowance
            logger.info(f"Setting default cutting_allowance to: {settings.cutting_allowance}")
            default_settings.hot_glue_per_meter = settings.hot_glue_per_meter
            default_settings.glue_with_activator_per_meter = settings.glue_with_activator_per_meter
            default_settings.silicone_per_meter = settings.silicone_per_meter
            default_settings.silicone_color_per_meter = settings.silicone_color_per_meter
            default_settings.pvc_cleaner_per_meter = settings.pvc_cleaner_per_meter
            default_settings.fixall_per_meter = settings.fixall_per_meter
            default_settings.glue_color_extra = settings.glue_color_extra
            
            db.session.commit()
            logger.info(f"Settings and defaults saved: cutting_allowance={default_settings.cutting_allowance}, fixall_per_meter={settings.fixall_per_meter}")
            
            # Check if it's an AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
                return jsonify({'status': 'success', 'message': 'Current settings saved as default!'})
            
            flash('Current settings saved as default!', 'success')
            return redirect(url_for('settings'))
            
        except Exception as e:
            logger.error(f"Error in save_as_default: {str(e)}")
            db.session.rollback()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
                return jsonify({'status': 'error', 'message': f'Error saving settings as default: {str(e)}'})
            flash(f'Error saving settings as default: {str(e)}', 'error')
            return redirect(url_for('settings'))

    @app.route('/cutting_layout', methods=['GET'])
    @limiter.limit("20/minute")
    def cutting_layout():
        try:
            active_client_id = session.get('active_client_id')
            if not active_client_id:
                flash('Please select a client first', 'warning')
                return redirect(url_for('clients'))
            
            active_client = Client.query.get(active_client_id)
            if not active_client:
                flash('Selected client not found', 'error')
                return redirect(url_for('clients'))
            
            # Get sills for the active client
            sills = Sill.query.filter_by(client_id=active_client_id).all()
            
            if not sills:
                flash('No sills found for this client', 'info')
                return render_template('cutting_layout.html', 
                                    client=active_client, 
                                    materials={})
            
            # Calculate cutting layout
            cutting_layouts = calculate_cutting_layout(sills)
            settings = Settings.query.first()
            
            return render_template('cutting_layout.html', 
                                client=active_client,
                                materials=cutting_layouts,
                                settings=settings)
        except Exception as e:
            logger.error(f"Error in cutting_layout route: {str(e)}")
            return render_template('error.html', error=str(e)), 500

    @app.route('/sills/<int:sill_id>', methods=['PUT', 'POST'])
    @limiter.limit("20/minute")
    def update_sill(sill_id):
        try:
            sill = Sill.query.get_or_404(sill_id)
            
            length_str = request.form.get('length')
            depth_str = request.form.get('depth')
            high_str = request.form.get('high')
            angle_str = request.form.get('angle')
            
            if not length_str or not depth_str:
                raise ValueError("Length and depth are required")
            
            sill.length = float(length_str)
            sill.depth = float(depth_str)
            sill.high = float(high_str) if high_str and high_str.strip() else None
            sill.angle = float(angle_str) if angle_str and angle_str.strip() else None
            sill.color = request.form.get('color') or ""
            sill.sill_type = request.form.get('sill_type') or ""
            sill.location = request.form.get('location') or ""
            sill.has_95mm = 'has_95mm' in request.form
            
            db.session.commit()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'status': 'success', 'message': 'Window sill updated successfully!'})
            
            flash('Window sill updated successfully!', 'success')
            return redirect(url_for('sills'))
        except Exception as e:
            db.session.rollback()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'status': 'error', 'message': f'Error updating window sill: {str(e)}'})
            flash(f'Error updating window sill: {str(e)}', 'error')
            return redirect(url_for('sills'))

    @app.route('/sills/<int:sill_id>', methods=['DELETE'])
    @limiter.limit("20/minute")
    def delete_sill(sill_id):
        try:
            sill = Sill.query.get_or_404(sill_id)
            db.session.delete(sill)
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'Window sill deleted successfully!'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'status': 'error', 'message': f'Error deleting window sill: {str(e)}'})

    @app.route('/set_active_client/<int:client_id>')
    def set_active_client(client_id):
        client = Client.query.get_or_404(client_id)
        session['active_client_id'] = client_id
        flash(f'Active client set to: {client.first_name} {client.last_name}', 'success')
        return redirect(request.referrer or url_for('clients'))

    @app.route('/add_client', methods=['POST'])
    @limiter.limit("20/minute")
    def add_client():
        try:
            client_data = {
                'first_name': request.form.get('first_name', '').strip(),
                'last_name': request.form.get('last_name', '').strip(),
                'phone': request.form.get('phone', '').strip(),
                'mobile': request.form.get('mobile', '').strip(),
                'email': request.form.get('email', '').strip(),
                'address': request.form.get('address', '').strip(),
                'town': request.form.get('town', '').strip(),
                'postal_code': request.form.get('postal_code', '').strip().upper(),
                'source': request.form.get('source', '').strip()
            }

            if not all([client_data['first_name'], client_data['last_name'], 
                       client_data['phone'], client_data['address'], 
                       client_data['town'], client_data['postal_code']]):
                flash('All fields except email and source are required!', 'error')
                return redirect(url_for('clients'))

            if not validate_phone(client_data['phone']):
                flash('Invalid phone number format!', 'error')
                return redirect(url_for('clients'))

            existing_client = Client.query.filter_by(phone=client_data['phone']).first()
            if existing_client:
                flash(f'Client with phone number {client_data["phone"]} already exists!', 'error')
                return redirect(url_for('clients'))

            if not validate_uk_postcode(client_data['postal_code']):
                flash('Invalid UK postcode format', 'error')
                return redirect(url_for('clients'))

            # Create Client instance manually to avoid **kwargs issues
            new_client = Client()
            new_client.first_name = client_data['first_name']
            new_client.last_name = client_data['last_name']
            new_client.phone = client_data['phone']
            new_client.mobile = client_data['mobile']
            new_client.email = client_data['email']
            new_client.address = client_data['address']
            new_client.town = client_data['town']
            new_client.postal_code = client_data['postal_code']
            new_client.source = client_data['source']
            
            db.session.add(new_client)
            db.session.commit()
            flash('Client added successfully!', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('A client with this phone number already exists!', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding client: {str(e)}', 'error')
        
        return redirect(url_for('clients'))

    @app.route('/delete_client/<int:client_id>', methods=['POST'])
    @limiter.limit("20/minute")
    def delete_client(client_id):
        try:
            client = Client.query.get_or_404(client_id)
            db.session.delete(client)
            db.session.commit()
            flash('Client deleted successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error deleting client: {str(e)}', 'error')
        
        return redirect(url_for('clients'))

    @app.route('/upload_contract', methods=['GET', 'POST'])
    @limiter.limit("20/minute")
    def upload_contract():
        if request.method == 'POST':
            logger.info("POST request received for upload_contract")
            try:
                if 'contract_file' not in request.files:
                    logger.error("No contract_file in request.files")
                    flash('No file selected', 'error')
                    return redirect(request.url)
                
                file = request.files['contract_file']
                logger.info(f"File received: {file.filename}")
                if file.filename == '':
                    logger.error("Empty filename")
                    flash('No file selected', 'error')
                    return redirect(request.url)
                
                if file and file.filename and allowed_file(file.filename, app.config['ALLOWED_EXTENSIONS']):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    logger.info(f"Saving file to: {filepath}")
                    file.save(filepath)
                    
                    # Copy image for preview
                    preview_path = os.path.join('static', 'uploads', 'preview.jpg')
                    os.makedirs(os.path.dirname(preview_path), exist_ok=True)
                    
                    # Convert and save as JPEG for preview
                    from PIL import Image
                    with Image.open(filepath) as img:
                        # Convert to RGB if needed (for PNG with transparency)
                        if img.mode in ('RGBA', 'LA', 'P'):
                            img = img.convert('RGB')
                        img.save(preview_path, 'JPEG', quality=85)
                        logger.info(f"Preview image saved to: {preview_path}")
                    
                    logger.info("Creating ContractParser...")
                    parser = ContractParser()
                    logger.info("Extracting text from image...")
                    extracted_text = parser.extract_text(filepath)
                    logger.info("Parsing client data...")
                    client_data = parser.parse_client_data(extracted_text)
                    logger.info("Parsing sills data...")
                    sills_data = parser.parse_sill_data(extracted_text)
                    
                    return render_template(
                        'verify_contract.html',
                        client_data=client_data,
                        sills_data=sills_data,
                        extracted_text=extracted_text
                    )
                
                flash('Invalid file type', 'error')
                return redirect(request.url)
                
            except Exception as e:
                import traceback
                logger.error(f"Error processing contract: {str(e)}")
                logger.error(f"Full traceback: {traceback.format_exc()}")
                flash(f'Error processing file: {str(e)}', 'error')
                return redirect(request.url)
        
        return render_template('upload_contract.html')

    @app.route('/save_contract', methods=['POST'])
    @limiter.limit("20/minute")
    def save_contract():
        try:
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            phone = request.form.get('phone')
            
            # Check if client already exists by first and last name
            existing_client = Client.query.filter_by(
                first_name=first_name, 
                last_name=last_name
            ).first()
            
            if existing_client:
                # Use existing client
                client = existing_client
                logger.info(f"Using existing client: {first_name} {last_name}")
            else:
                # Create new client - only use fields that exist in Client model
                client_data = {
                    'first_name': first_name,
                    'last_name': last_name,
                    'address': request.form.get('address', ''),
                    'town': request.form.get('town', ''),
                    'postal_code': request.form.get('postal_code', ''),
                    'phone': phone,
                    'mobile': request.form.get('mobile', ''),
                    'email': request.form.get('email', ''),
                    'source': request.form.get('source', '')
                }
                
                # Create Client instance manually to avoid **kwargs issues
                client = Client()
                client.first_name = client_data['first_name']
                client.last_name = client_data['last_name']
                client.address = client_data['address']
                client.town = client_data['town']
                client.postal_code = client_data['postal_code']
                client.phone = client_data['phone']
                client.mobile = client_data['mobile']
                client.email = client_data['email']
                client.source = client_data['source']
                
                db.session.add(client)
                db.session.flush()
                logger.info(f"Created new client: {first_name} {last_name} with phone: {phone}")
            
            sill_count = int(request.form.get('sill_count', 0))
            for i in range(sill_count):
                length_str = request.form.get(f'sill_{i}_length')
                depth_str = request.form.get(f'sill_{i}_depth')
                
                if not length_str or not depth_str:
                    raise ValueError(f"Length and depth are required for sill {i}")
                
                new_sill = Sill()
                new_sill.client_id = client.id
                new_sill.order_number = Sill.generate_order_number()
                new_sill.length = float(length_str)
                new_sill.depth = float(depth_str)
                new_sill.location = request.form.get(f'sill_{i}_location') or ""
                new_sill.color = request.form.get(f'sill_{i}_color') or ""
                new_sill.sill_type = request.form.get(f'sill_{i}_type') or ""
                new_sill.has_95mm = request.form.get(f'sill_{i}_has_95mm') == 'on'
                db.session.add(new_sill)
            
            db.session.commit()
            
            if existing_client:
                flash(f'Contract saved successfully. Added {sill_count} sills to existing client: {client.first_name} {client.last_name}', 'success')
            else:
                flash(f'Contract saved successfully. Created new client: {client.first_name} {client.last_name} with {sill_count} sills', 'success')
            
            return redirect(url_for('clients'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error saving contract: {str(e)}")
            flash(f'Error saving contract: {str(e)}', 'error')
            return redirect(url_for('upload_contract'))

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        logger.error(f"404 error: {request.url}")
        return render_template('error.html',
                            error="Page not found",
                            error_type="404 Not Found",
                            error_details=f"URL: {request.url}"), 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error("500 error", exc_info=True)
        db.session.rollback()
        return render_template('error.html',
                            error="Internal server error",
                            error_type="500 Internal Server Error",
                            error_details=str(error)), 500

    @app.errorhandler(429)
    def ratelimit_handler(error):
        logger.error(f"Rate limit exceeded: {error}")
        return render_template('error.html',
                            error="Rate limit exceeded.",
                            error_type="429 Too Many Requests",
                            error_details=str(error)), 429

def allowed_file(filename: str, allowed_extensions: set) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def calculate_materials_for_sills(sills: List[Sill], settings: Settings) -> Dict:
    total_main_boards_length = sum(
        sill.length + settings.cutting_allowance 
        for sill in sills
    )

    summed_materials = {
        'boards': {},
        'glues': {},
        'silicones': {},
        'other': {}
    }
    
    # Get cutting layout to count actual boards needed
    cutting_layouts = calculate_cutting_layout(sills)
    
    # Count actual boards from cutting layout with total length
    for board_type, boards in cutting_layouts.items():
        board_count = len(boards)  # Number of physical boards needed
        total_length = sum(board['total_length'] for board in boards) / 1000  # Convert to meters
        summed_materials['boards'][board_type] = {
            'amount': board_count,
            'total_length': total_length,
            'unit': 'boards'
        }

    # Calculate materials based on total length
    # Hot glue and fixall white should have same amount
    fixall_base_amount = (total_main_boards_length / 1000) * settings.fixall_per_meter
    colored_boards_length = sum(
        sill.length + settings.cutting_allowance 
        for sill in sills 
        if sill.color != 'White'
    )
    fixall_extra_amount = (colored_boards_length / 1000) * settings.glue_color_extra
    
    total_fixall_amount = fixall_base_amount + fixall_extra_amount
    
    # Hot glue should match fixall white amount
    summed_materials['glues']["Hot Glue"] = {
        'amount': math.ceil(total_fixall_amount),
        'unit': 'sticks'
    }
    
    summed_materials['glues']["Fixall White"] = {
        'amount': math.ceil(total_fixall_amount),
        'unit': 'ml'
    }

    s2_clear_amount = (total_main_boards_length / 1000) * settings.silicone_per_meter
    summed_materials['silicones']["S2 Clear Silicone"] = {'amount': s2_clear_amount, 'unit': 'bottles'}

    color_silicones = {}
    for sill in sills:
        silicone_length = sill.length + settings.cutting_allowance
        silicone_name = "Silicone White" if sill.color == 'White' else f"Silicone ({sill.color})"
        
        if silicone_name not in color_silicones:
            color_silicones[silicone_name] = 0
        color_silicones[silicone_name] += (silicone_length / 1000) * settings.silicone_color_per_meter

    for silicone_name, amount in color_silicones.items():
        summed_materials['silicones'][silicone_name] = {'amount': amount, 'unit': 'bottles'}

    pvc_cleaner_amount = (total_main_boards_length / 1000) * settings.pvc_cleaner_per_meter
    summed_materials['other']["PVC Cleaner"] = {'amount': pvc_cleaner_amount, 'unit': 'bottles'}

    return {
        'boards': [{'name': name, 'amount': data['amount'], 'total_length': data.get('total_length', 0), 'unit': data['unit']} 
                  for name, data in summed_materials['boards'].items()],
        'glues': [{'name': name, 'amount': data['amount'], 'unit': data['unit']} 
                 for name, data in summed_materials['glues'].items()],
        'silicones': [{'name': name, 'amount': data['amount'], 'unit': data['unit']} 
                     for name, data in summed_materials['silicones'].items()],
        'other': [{'name': name, 'amount': data['amount'], 'unit': data['unit']} 
                 for name, data in summed_materials['other'].items()]
    }

def calculate_costs_for_sills(sills: List[Sill], prices: MaterialPrices) -> List[Dict]:
    sills_with_costs = []
    for sill in sills:
        material_cost = calculate_material_cost(sill, prices)
        fitting_cost = calculate_fitting_cost(sill, prices)
        total_sill_cost = material_cost + fitting_cost

        sills_with_costs.append({
            'sill': sill,
            'material_cost': material_cost,
            'fitting_cost': fitting_cost,
            'total_cost': total_sill_cost
        })

    return sills_with_costs

def calculate_material_cost(sill: Sill, prices: MaterialPrices) -> float:
    material_cost = 0
    standard_board_length = 6000
    
    # Board costs
    boards_needed = math.ceil(sill.length / standard_board_length)
    if sill.sill_type == 'Straight':
        material_cost += boards_needed * prices.gp_board_price
    else:
        material_cost += boards_needed * prices.capit_board_price

    if sill.has_95mm:
        boards_95mm_needed = math.ceil(sill.length / standard_board_length)
        material_cost += boards_95mm_needed * prices.board_95mm_price

    # Hot Glue
    if sill.color == 'White':
        hot_glue_sticks = math.ceil(sill.length / 500)
        material_cost += hot_glue_sticks * prices.hot_glue_price

    # Silicone
    silicone_tubes = math.ceil(sill.length / 3000)
    material_cost += silicone_tubes * prices.silicone_price
    material_cost += silicone_tubes * prices.s2_clear_silicone_price

    return material_cost

def calculate_fitting_cost(sill: Sill, prices: MaterialPrices) -> float:
    fitting_cost = 0
    
    if sill.sill_type == 'Straight':
        fitting_cost = prices.fitting_price_straight
    elif sill.sill_type == 'C-shaped':
        fitting_cost = prices.fitting_price_c_shape
    elif sill.sill_type == 'Bay-Curve shaped':
        fitting_cost = prices.fitting_price_bay_curve
    elif sill.sill_type == 'Conservatory':
        fitting_cost = prices.fitting_price_conservatory
        
    if sill.has_95mm:
        fitting_cost += prices.fitting_price_95mm

    return fitting_cost 