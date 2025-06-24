from app import app, db, Settings, DefaultSettings, MaterialPrices

with app.app_context():
    # Create all tables
    db.create_all()

    # Create default settings
    default_settings = DefaultSettings(
        plate_length=6000,  # mm
        length_95mm=200,    # mm
        cutting_allowance=2, # mm
        hot_glue_per_meter=0.05,  # sticks/m
        glue_with_activator_per_meter=0.05,  # ml/bottle
        silicone_per_meter=0.1,  # ml/tube
        silicone_color_per_meter=0.1,  # ml/tube
        pvc_cleaner_per_meter=0.1,  # ml/bottle
        fixall_per_meter=0.1,  # ml/bottle
        glue_color_extra=0.05  # ml/bottle
    )

    settings = Settings(
        plate_length=6000,  # mm
        length_95mm=200,    # mm
        cutting_allowance=2, # mm
        hot_glue_per_meter=0.05,  # sticks/m
        glue_with_activator_per_meter=0.05,  # ml/bottle
        silicone_per_meter=0.1,  # ml/tube
        silicone_color_per_meter=0.1,  # ml/tube
        pvc_cleaner_per_meter=0.1,  # ml/bottle
        fixall_per_meter=0.1,  # ml/bottle
        glue_color_extra=0.05  # ml/bottle
    )

    material_prices = MaterialPrices(
        gp_board_price=10.0,
        capit_board_price=10.0,
        board_95mm_price=10.0,
        glue_price=10.0,
        hot_glue_price=0.5,
        silicone_price=10.0,
        silicone_color_price=10.0,
        pvc_cleaner_price=10.0,
        s2_clear_silicone_price=10.0,
        fixall_white_price=10.0,
        glue_with_activator_price=10.0,
        fitting_price_straight=35.0,
        fitting_price_c_shape=35.0,
        fitting_price_bay_curve=50.0,
        fitting_price_conservatory=35.0,
        fitting_price_95mm=5.0
    )

    db.session.add(default_settings)
    db.session.add(settings)
    db.session.add(material_prices)
    db.session.commit()

    print("Database initialized successfully!")
