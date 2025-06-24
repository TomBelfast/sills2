import re
import math
from typing import Dict, List, Tuple, Optional
from models import Settings, Sill

def validate_uk_postcode(postcode: str) -> bool:
    """Validate UK postcode format."""
    pattern = r'^[A-Za-z]{1,2}[0-9][A-Za-z0-9]? [0-9][A-Za-z]{2}$'
    return bool(re.match(pattern, postcode.upper()))

def validate_phone(phone: str) -> bool:
    """Validate phone number format."""
    pattern = r'^\+?[\d\s-]{10,}$'
    return bool(re.match(pattern, phone))

def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def get_capit_board_size(depth: float) -> int:
    """Determine the appropriate Capit Board size based on depth."""
    if depth <= 210:
        return 225
    elif depth <= 240:
        return 250
    else:
        return 300

def calculate_materials(sill: Sill) -> Dict[str, List[Dict[str, float]]]:
    """Calculate materials needed for a window sill."""
    settings = Settings.query.first()
    if not settings:
        return {}

    materials = {
        'boards': [],  # Boards
        'glues': [],   # Adhesives
        'silicones': [], # Silicones
        'other': []    # Other materials
    }

    # Add Cutting Allowance to length
    total_length = sill.length + settings.cutting_allowance
    material_length = 0

    # Calculate board requirements
    if sill.sill_type == 'Straight':
        board_name = f"GP Board - {sill.color}"
        materials['boards'].append({
            'name': board_name,
            'amount': total_length / 1000,
            'unit': 'm'
        })
        material_length += total_length
    else:
        # Main Capit Board
        capit_size = get_capit_board_size(sill.depth)
        board_name = f"Capit Board {capit_size}mm - {sill.color}"
        materials['boards'].append({
            'name': board_name,
            'amount': total_length / 1000,
            'unit': 'm'
        })
        material_length += total_length

        # Additional Capit Board
        additional_board_size = "150mm" if sill.color == 'White' else "175mm"
        materials['boards'].append({
            'name': f"Capit Board {additional_board_size} - {sill.color}",
            'amount': total_length / 1000,
            'unit': 'm'
        })

    # 95mm board if used
    if sill.has_95mm:
        materials['boards'].append({
            'name': f"95mm Board - {sill.color}",
            'amount': total_length / 1000,
            'unit': 'm'
        })

    # Calculate glue materials
    if sill.color != 'White':
        # Glue with Activator for colored sills
        materials['glues'].append({
            'name': "Glue with Activator",
            'amount': (material_length / 1000) * settings.glue_with_activator_per_meter,
            'unit': 'ml'
        })
    else:
        # Hot Glue for white sills
        materials['glues'].append({
            'name': "Hot Glue",
            'amount': (material_length / 1000) * settings.hot_glue_per_meter,
            'unit': 'sticks'
        })

    # Add Fixall White
    materials['glues'].append({
        'name': "Fixall White",
        'amount': (material_length / 1000) * settings.fixall_per_meter,
        'unit': 'ml'
    })

    # Calculate silicone usage
    materials['silicones'].append({
        'name': "S2 Clear Silicone",
        'amount': (material_length / 1000) * settings.silicone_per_meter,
        'unit': 'ml'
    })

    silicone_name = "Silicone White" if sill.color == 'White' else f"Silicone ({sill.color})"
    materials['silicones'].append({
        'name': silicone_name,
        'amount': (material_length / 1000) * settings.silicone_color_per_meter,
        'unit': 'ml'
    })

    # Calculate PVC cleaner
    materials['other'].append({
        'name': "PVC Cleaner",
        'amount': (material_length / 1000) * settings.pvc_cleaner_per_meter,
        'unit': 'ml'
    })

    return materials

def calculate_cutting_layout(sills: List[Sill], board_length: int = 5000) -> Dict[str, List[Dict]]:
    """Calculate optimal cutting layout for boards."""
    all_materials = {}
    settings = Settings.query.first()
    
    # Default cutting allowance if no settings found
    cutting_allowance = settings.cutting_allowance if settings else 2.0
    
    for sill in sills:
        sill_materials = calculate_materials(sill)
        
        for board in sill_materials['boards']:
            board_key = board['name']
            
            if board_key not in all_materials:
                all_materials[board_key] = []
                
            sill_length = sill.length + cutting_allowance
            remaining_length = sill_length
            
            while remaining_length > 0:
                current_length = min(remaining_length, board_length)
                board_found = False
                
                for board_pieces in all_materials[board_key]:
                    total_length = sum(piece['length'] for piece in board_pieces['pieces'])
                    if total_length + current_length <= board_length:
                        board_pieces['pieces'].append({
                            'id': sill.id,
                            'length': current_length,
                            'original_length': sill.length,
                            'cutting_allowance': cutting_allowance,
                            'location': sill.location,
                            'color': sill.color
                        })
                        board_pieces['total_length'] = total_length + current_length
                        board_pieces['remaining_length'] = board_length - (total_length + current_length)
                        board_found = True
                        break
                
                if not board_found:
                    all_materials[board_key].append({
                        'pieces': [{
                            'id': sill.id,
                            'length': current_length,
                            'original_length': sill.length,
                            'cutting_allowance': cutting_allowance,
                            'location': sill.location,
                            'color': sill.color
                        }],
                        'total_length': current_length,
                        'remaining_length': board_length - current_length
                    })
                
                remaining_length -= current_length
    
    return all_materials 