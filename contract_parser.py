import os
import base64
import io
import logging
import re
import time
from typing import Dict, List, Tuple, Optional
from PIL import Image
from openai import OpenAI as OpenAIClient

logger = logging.getLogger(__name__)

class ContractParser:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing ContractParser...")
        api_key = os.getenv('OPENAI_API_KEY')
        self.logger.info(f"API key loaded: {'SET' if api_key else 'NOT SET'}")
        self.client = OpenAIClient(api_key=api_key)
        self.logger.info("OpenAI client created successfully")
        self.max_retries = 3
        self.retry_delay = 2

    def extract_text(self, image_path: str) -> str:
        """
        Extracts text from an image using OpenAI API with retry mechanism.
        """
        self.logger.info(f"Starting text extraction from: {image_path}")
        last_error = None
        extracted_text = ""

        for attempt in range(self.max_retries):
            try:
                self.logger.info(f"Attempt {attempt + 1} to extract text")
                # Load and convert image to base64
                with open(image_path, 'rb') as image_file:
                    image_data = image_file.read()
                    base64_image = base64.b64encode(image_data).decode('utf-8')
                    self.logger.info(f"Image loaded and encoded, size: {len(image_data)} bytes")

                # Prepare API request with detailed instructions
                self.logger.info("Sending request to OpenAI API...")
                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": """Analyze this contract and extract the following information:

1. Client Details:
   - Full name (including title if present)
   - Complete street address (house number and street name only - NO town or postcode)
   - Town/city name (separate from address)
   - Post code (UK format)
   - Phone number (landline)
   - Mobile number (if different from phone)
   - Email address
   - Contract source

2. Window Sills:
   - Location in the house/building
   - Sill type (ONLY: Straight, C-shaped, Bay-Curve shaped, or Conservatory)
   - Color (ONLY the color name like: White, Black Grain, Oak, Cream, Anthracite Grey, etc.)
   - Dimensions in millimeters
   - Whether it has a 95mm side (U/Side)

IMPORTANT: Keep Type and Color completely separate. Do NOT combine them.

Return the data in exactly this format:

Client Details:
- Name: [Full Name]
- Address: [Street Address ONLY - no town/postcode]
- Town: [Town/City name only]
- Post Code: [Code]
- Phone: [Landline Number]
- Mobile: [Mobile Number if different]
- Email: [Email]
- Source: [Source]

Window Sills:
1. Location: [Place]
   Type: [Straight/C-shaped/Bay-Curve shaped/Conservatory ONLY]
   Color: [Color name ONLY]
   Size: [Size in mm]
   U/Side: [Yes/No]

2. Location: [Place]
   Type: [Straight/C-shaped/Bay-Curve shaped/Conservatory ONLY]
   Color: [Color name ONLY]
   Size: [Size in mm]
   U/Side: [Yes/No]

[Continue for all window sills found]"""
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{base64_image}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=2000,
                    temperature=0.3
                )

                # Get text from response
                self.logger.info("Received response from OpenAI API")
                extracted_text = response.choices[0].message.content
                self.logger.info(f"Extracted text length: {len(extracted_text)} characters")
                
                # Check if text contains required sections
                if "unable" in extracted_text.lower():
                    raise ValueError("Model could not extract text from image")
                
                self.logger.info(f"Text extraction successful on attempt {attempt + 1}")
                return extracted_text

            except Exception as e:
                last_error = e
                self.logger.warning(f"Error during text extraction (attempt {attempt + 1}): {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                continue

        self.logger.error(f"Failed to extract text after {self.max_retries} attempts. Last error: {str(last_error)}")
        raise last_error

    def _validate_extracted_text(self, text: str) -> bool:
        """
        Validates if the extracted text contains all required information.
        """
        required_client_fields = ['Name:', 'Address:', 'Post Code:', 'Phone:']
        required_sill_fields = ['Location:', 'Type:', 'Color:', 'Size:']

        # Check client fields
        for field in required_client_fields:
            if not re.search(f'{field}\s*[^\n]+', text):
                self.logger.warning(f"Missing required client field: {field}")
                return False

        # Check if there's at least one window sill
        sill_sections = re.findall(r'\d+\.\s*Location:', text)
        if not sill_sections:
            self.logger.warning("Missing window sills section")
            return False

        # Check sill fields
        sill_text = text[text.find('Window Sills:'):]
        for field in required_sill_fields:
            if not re.search(f'{field}\s*[^\n]+', sill_text):
                self.logger.warning(f"Missing required sill field: {field}")
                return False

        return True

    def parse_client_data(self, text: str) -> Dict[str, str]:
        """
        Parses client data from the text.
        """
        try:
            client_data = {
                'first_name': '',
                'last_name': '',
                'phone': '',
                'mobile': '',
                'email': '',
                'address': '',
                'town': '',
                'postal_code': '',
                'source': ''
            }

            # Search for client data patterns
            name_match = re.search(r'Name:\s*([^\n]+)', text)
            if name_match:
                full_name = name_match.group(1).strip()
                name_parts = full_name.split()
                if len(name_parts) >= 2:
                    client_data['first_name'] = name_parts[0]
                    client_data['last_name'] = ' '.join(name_parts[1:])

            # Parse address (should be street only)
            address_match = re.search(r'Address:\s*([^\n]+)', text)
            if address_match:
                client_data['address'] = address_match.group(1).strip()

            # Parse town (separate field)
            town_match = re.search(r'Town:\s*([^\n]+)', text)
            if town_match:
                client_data['town'] = town_match.group(1).strip()
            
            # Parse postal code
            postal_match = re.search(r'Post Code:\s*([^\n]+)', text)
            if postal_match:
                client_data['postal_code'] = postal_match.group(1).strip()

            # Parse phone number
            phone_match = re.search(r'Phone:\s*([^\n]+)', text)
            if phone_match:
                client_data['phone'] = phone_match.group(1).strip()

            # Parse mobile number
            mobile_match = re.search(r'Mobile:\s*([^\n]+)', text)
            if mobile_match:
                client_data['mobile'] = mobile_match.group(1).strip()

            # Parse email
            email_match = re.search(r'Email:\s*([^\n]+)', text)
            if email_match:
                client_data['email'] = email_match.group(1).strip()

            source_match = re.search(r'Source:\s*([^\n]+)', text)
            if source_match:
                client_data['source'] = source_match.group(1).strip()

            self.logger.info(f"Parsed client data: {client_data}")
            return client_data

        except Exception as e:
            self.logger.error(f"Error parsing client data: {str(e)}")
            raise

    def parse_sill_data(self, text: str) -> List[Dict[str, str]]:
        """
        Parses window sill data from the text.
        """
        try:
            sills_data = []
            
            self.logger.info("Starting to parse sill data")
            self.logger.info(f"Full text to parse: {text}")
            
            # Find "Window Sills:" section and get all text after it
            window_sills_start = text.find('Window Sills:')
            if window_sills_start == -1:
                self.logger.warning("Window Sills section not found")
                # Try alternative patterns
                alt_patterns = ['Sills:', 'Window sills:', 'WINDOW SILLS:']
                for pattern in alt_patterns:
                    window_sills_start = text.find(pattern)
                    if window_sills_start != -1:
                        self.logger.info(f"Found sills section with pattern: {pattern}")
                        break
                
                if window_sills_start == -1:
                    self.logger.error("No Window Sills section found with any pattern")
                    return sills_data

            # Get the sills text starting after "Window Sills:"
            sills_text = text[window_sills_start:].split(':', 1)[1].strip()
            self.logger.info(f"Sills section text: {sills_text}")
            
            # Find all individual sill entries using regex to match numbered sections
            sill_matches = re.findall(r'(\d+\.\s*Location:.*?)(?=\n\d+\.\s*Location:|\Z)', sills_text, re.DOTALL)
            self.logger.info(f"Found sill matches: {len(sill_matches)}")
            
            if not sill_matches:
                # If no matches found, try a different approach - split on numbered lines
                sill_sections = re.split(r'\n(?=\d+\.)', sills_text)
                self.logger.info(f"Split on newlines with numbers: {sill_sections}")
                
                # Remove empty sections and clean up
                sill_sections = [s.strip() for s in sill_sections if s.strip()]
                self.logger.info(f"After cleaning: {sill_sections} (count: {len(sill_sections)})")
            else:
                # Use the regex matches as sections
                sill_sections = [match.strip() for match in sill_matches]
                self.logger.info(f"Using regex matches as sections: {len(sill_sections)} sections found")
            
            for i, section in enumerate(sill_sections, 1):
                self.logger.info(f"Processing section {i}: '{section}'")
                
                sill = {
                    'number': str(i),
                    'location': 'Unknown',
                    'type': '',
                    'color': '',
                    'size': '',
                    'has_95mm': False
                }

                # Parse sill details
                location_match = re.search(r'Location:\s*([^\n]+)', section)
                if location_match:
                    location_value = location_match.group(1).strip()
                    if location_value and location_value.lower() not in ['n/a', 'none', '']:
                        sill['location'] = location_value
                        self.logger.info(f"Found location: {sill['location']}")

                # Parse Type field - this often contains both color and type info
                type_match = re.search(r'Type:\s*([^\n]+)', section)
                if type_match:
                    type_full = type_match.group(1).strip()
                    self.logger.info(f"Found full type string: {type_full}")
                    
                    # Split color and type from the Type field
                    # Common patterns: "Black Grain Straight", "White Straight", "Oak Bay"
                    color_part = ""
                    type_part = ""
                    
                    # Known sill types
                    sill_types = ['straight', 'bay', 'c-shaped', 'conservatory', 'bay-curve shaped']
                    
                    # Check if any sill type is at the end
                    type_full_lower = type_full.lower()
                    for sill_type in sill_types:
                        if type_full_lower.endswith(sill_type):
                            type_part = sill_type.title()
                            color_part = type_full[:-len(sill_type)].strip()
                            break
                    
                    # If no type found at end, assume whole string is color
                    if not type_part:
                        color_part = type_full
                        type_part = "Straight"  # Default type
                    
                    # Set color from Type field if Color field is empty or N/A
                    if color_part and color_part.lower() not in ['n/a', 'none', '']:
                        sill['color'] = color_part
                        self.logger.info(f"Extracted color from type: {sill['color']}")
                    
                    if type_part:
                        sill['type'] = type_part
                        self.logger.info(f"Extracted type: {sill['type']}")

                # Parse Color field separately (might override Type field color)
                color_match = re.search(r'Color:\s*([^\n]+)', section)
                if color_match:
                    color_value = color_match.group(1).strip()
                    if color_value and color_value.lower() not in ['n/a', 'none', '']:
                        sill['color'] = color_value
                        self.logger.info(f"Found explicit color: {sill['color']}")

                # Parse size
                size_match = re.search(r'Size:\s*(\d+(?:\.\d+)?)\s*(?:mm|cm)?', section)
                if size_match:
                    size_value = size_match.group(1)
                    if size_value and size_value != '0':
                        sill['size'] = size_value
                        self.logger.info(f"Found size: {sill['size']}")

                # Parse U/Side
                u_side_match = re.search(r'U/Side:\s*([^\n]+)', section)
                if u_side_match:
                    u_side_value = u_side_match.group(1).strip().lower()
                    if u_side_value and u_side_value not in ['n/a', 'none', '']:
                        sill['has_95mm'] = u_side_value in ['yes', 'true', '1', 'y']
                        self.logger.info(f"Found U/Side: {u_side_value} -> {sill['has_95mm']}")

                # Only add sill if it has meaningful data (location and size at minimum)
                if sill['location'] != 'Unknown' and sill['size']:
                    self.logger.info(f"Parsed window sill {i}: {sill}")
                    sills_data.append(sill)
                else:
                    self.logger.warning(f"Skipping sill {i} - insufficient data: {sill}")

            self.logger.info(f"Total window sills parsed: {len(sills_data)}")
            return sills_data

        except Exception as e:
            self.logger.error(f"Error parsing window sill data: {str(e)}")
            raise

    def parse_contract(self, image_path: str) -> Tuple[Dict[str, str], List[Dict[str, str]]]:
        """
        Parses contract from image and returns client data and window sill data.
        """
        try:
            # Save copy of image for preview
            preview_path = os.path.join('static', 'uploads', 'preview.jpg')
            os.makedirs(os.path.dirname(preview_path), exist_ok=True)
            
            # Copy and convert image to JPEG
            with Image.open(image_path) as img:
                img.save(preview_path, 'JPEG')
            
            # Extract text from image
            text = self.extract_text(image_path)
            self.logger.info(f"Full contract text: {text}")
            
            # Parse client and sill data
            client_data = self.parse_client_data(text)
            sills_data = self.parse_sill_data(text)
            
            return client_data, sills_data

        except Exception as e:
            self.logger.error(f"Error parsing contract: {str(e)}")
            raise 