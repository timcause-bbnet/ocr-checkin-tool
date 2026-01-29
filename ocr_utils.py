import cv2
import numpy as np
from rapidocr_onnxruntime import RapidOCR
from PIL import Image
import re
import opencc
import datetime

# Initialize OCR and Converter
engine = RapidOCR()
cc = opencc.OpenCC('s2t')  # Convert Simplified to Traditional

def preprocess_image(image_file):
    image = Image.open(image_file)
    image = image.convert('RGB')
    img_array = np.array(image)
    return img_array

def normalize_date_roc(roc_date_str):
    # e.g. 77年5月20日 or 110.1.1
    try:
        # Simple extraction of numbers
        nums = re.findall(r'\d+', roc_date_str)
        if len(nums) >= 3:
            year, month, day = int(nums[0]), int(nums[1]), int(nums[2])
            return f"{year + 1911:04d}/{month:02d}/{day:02d}"
    except:
        pass
    return roc_date_str

def normalize_date_mrz(yymmdd):
    # Heuristic: if yy > 30 -> 19yy, else 20yy (Adjust as needed)
    if not yymmdd or len(yymmdd) != 6: 
        return yymmdd
    try:
        yy = int(yymmdd[:2])
        mm = int(yymmdd[2:4])
        dd = int(yymmdd[4:6])
        current_year = datetime.datetime.now().year % 100
        # Passport logical guess: if expire date, usually future. If dob, usually past.
        # But here we assume DOB context mostly or we check context.
        # Let's assume DOB for now:
        # If yy is significantly larger than current year, it's probably 19yy.
        full_year = 2000 + yy if yy <= current_year + 5 else 1900 + yy
        return f"{full_year:04d}/{mm:02d}/{dd:02d}"
    except:
        return yymmdd

def extract_mrz_info(lines):
    info = {}
    
    for line in lines:
        clean = line.replace(" ", "").upper()
        
        # 1. Parsing Line 2 (The data line)
        # Regex: Core fields only [PP][Check][Nat][DOB][Check][Sex]
        # We stop at Sex to allow split lines (where Expiry is on next OCR line)
        # Matches: [Passport 9][Check 1][Nat 3][DOB 6][Check 1][Sex 1]
        match_l2 = re.search(r'([A-Z0-9<]{9})([0-9O]?)([A-Z0-9<]{3})([0-9O]{6})([0-9O]?)([MF<])', clean)
        
        if match_l2:
            pp_no = match_l2.group(1).replace("<", "")
            nat = match_l2.group(3).replace("<", "").replace("0", "O")
            
            # Date: Replace O with 0
            dob = match_l2.group(4).replace("O", "0")
            
            sex = match_l2.group(6)
            
            info['Passport Number'] = pp_no
            info['BirthdayRaw'] = dob
            info['Birthday'] = normalize_date_mrz(dob)
            info['Nationality Code'] = nat
            info['MRZ Line 2'] = clean
            
            if sex == 'M': info['Gender'] = '男性'
            elif sex == 'F': info['Gender'] = '女性'
            
            # Map common codes
            country_map = {
                'D': '德國 (Germany)', 'DEU': '德國 (Germany)',
                'TWN': '台灣', 'CHN': '中國', 
                'HKG': '香港', 'MAC': '澳門',
                'USA': '美國', 'JPN': '日本',
                'KOR': '韓國 (South Korea)',
                'GBR': '英國 (UK)', 'CAN': '加拿大', 'AUS': '澳洲',
                'FRA': '法國', 'ITA': '義大利', 'ESP': '西班牙',
                'THA': '泰國 (Thailand)', 'VNM': '越南'
            }
            info['Nationality'] = country_map.get(nat, nat)
            
            # Optional: Try to get Expiry if present in this line
            try:
                remainder = clean[match_l2.end():]
                if len(remainder) >= 6:
                    exp = remainder[:6].replace("O", "0")
                    # Strict digit check?
                    if re.match(r'[0-9]{6}', exp): 
                        info['Expiry'] = normalize_date_mrz(exp)
            except:
                pass

        # 2. Parsing Line 1 (Name line)
        if clean.startswith("P") and "<<" in clean:
            if len(clean) > 5:
                line1_country = clean[2:5].replace("<", "").replace("0", "O")
                name_part = clean[5:]
                
                names = name_part.split("<<")
                surname = names[0].replace("<", "")
                given = names[1].split("<")[0] if len(names) > 1 else ""
                
                info['MRZ Name'] = f"{surname}, {given}"
                info['MRZ Line 1'] = clean
                
                if 'Nationality' not in info and line1_country:
                     info['Nationality Code'] = line1_country
                     country_map = {
                        'D': '德國 (Germany)', 'DEU': '德國 (Germany)',
                        'TWN': '台灣', 'CHN': '中國', 
                        'HKG': '香港', 'MAC': '澳門',
                        'USA': '美國', 'JPN': '日本',
                        'KOR': '韓國 (South Korea)',
                        'GBR': '英國 (UK)', 'CAN': '加拿大', 'AUS': '澳洲',
                        'FRA': '法國', 'ITA': '義大利', 'ESP': '西班牙',
                        'THA': '泰國 (Thailand)', 'VNM': '越南'
                     }
                     info['Nationality'] = country_map.get(line1_country, line1_country)

    return info

def process_document(image_file):
    img = preprocess_image(image_file)
    result, elapse = engine(img)
    
    if not result:
        return {"error": "No text detected"}

    lines = [cc.convert(res[1]) for res in result]
    full_text = "\n".join(lines)
    print("DEBUG OCR:\n", full_text) # Helpful for console debug
    
    raw_data = {
        "Type": "Unknown",
        "Raw Lines": lines
    }
    
    # Logic Branching
    # 1. Try to find MRZ first (Strongest signal for Passports and many IDs)
    mrz_check = extract_mrz_info(lines)
    if mrz_check:
        raw_data["Type"] = "Passport (MRZ)"
        raw_data.update(parse_passport(lines))
    elif "身分證" in full_text and ("國民" in full_text or "中華民國" in full_text or "統一編號" in full_text):
        raw_data["Type"] = "Taiwan ID"
        raw_data.update(parse_taiwan_id(lines))
    else:
        # Fallback to Passport logic scan if keywords present
        if "PASSPORT" in full_text.upper() or "護照" in full_text:
             raw_data["Type"] = "Passport"
             raw_data.update(parse_passport(lines))
        else:
             # Last resort: Try Taiwan ID parsing even without keywords (often keywords are small/blurry)
             raw_data["Type"] = "Taiwan ID (Fallback)"
             raw_data.update(parse_taiwan_id(lines))
    
    # Standardization
    standardized = standardize_to_checkin(raw_data)
    
    return {
        "Standardized": standardized,
        "Detailed": raw_data
    }

def parse_taiwan_id(lines):
    info = {'Nationality': '台灣'}
    
    for i, line in enumerate(lines):
        cleaned = line.strip().replace(" ", "")
        
        # Name Anchor
        if "姓名" in line:
            val = line.replace("姓名", "").strip()
            # If name is empty, it might be on the next line
            if not val and i+1 < len(lines): 
                val = lines[i+1]
            info['Name'] = val
            
        # DOB
        if "出生" in line:
            # Try to grab date string even if spaced out
            # Combine current line + next line to search for date pattern
            context = line + (lines[i+1] if i+1 < len(lines) else "")
            match = re.search(r'(\d{2,3})[\.年 ]*(\d{1,2})[\.月 ]*(\d{1,2})', context)
            if match:
                 info['Birthday'] = normalize_date_roc(f"{match.group(1)}年{match.group(2)}月{match.group(3)}")

        # Address
        if "住址" in line:
            val = line.replace("住址", "").strip()
            if len(val) < 3 and i+1 < len(lines): val += lines[i+1]
            info['Address'] = val

        # ID Regex
        id_match = re.search(r'[A-Z][12]\d{8}', cleaned)
        if id_match:
            uid = id_match.group(0)
            info['ID Number'] = uid
            if uid[1] == '1': info['Gender'] = '男性'
            elif uid[1] == '2': info['Gender'] = '女性'

    # Fallback: If Name still missing, guess from top lines
    if not info.get('Name'):
        ignore = ['中華民國', '國民身分證', '身分證', '姓名', '樣本', '樣張']
        for line in lines[:5]:
            t = line.strip().replace(" ", "")
            # Chinese Name pattern: 2-4 chars
            if re.match(r'^[\u4e00-\u9fa5]{2,4}$', t) and t not in ignore:
                info['Name'] = t
                break
                
    return info

def parse_passport(lines):
    info = {}
    
    # 1. Try Anchor "姓名" first (Reliable for China/Taiwan Passports)
    for i, line in enumerate(lines):
        # Look for "姓名" often combined with "NAME"
        if "姓名" in line:
            # Check next line for the actual name (Common layout)
            if i + 1 < len(lines):
                candidate = lines[i+1].strip()
                # If looks like Chinese name (2-5 chars)
                if re.match(r'^[\u4e00-\u9fa5]{2,5}$', candidate):
                    info['Name'] = candidate
                    break

    # 2. MRZ Extraction (Primary Source for most data)
    info.update(extract_mrz_info(lines))
    
    # 3. Fallback: visual scan for first Chinese Name-like string if we didn't find one yet
    if 'Name' not in info:
        ignore_list = [
            '中華民國', '護照', 'PASSPORT', '中華人民共和國', '簽發', '公安部', 
            'Type', 'Code', '地點', '機關', '姓名', '性別', '出生', '備註', 
            '觀察', '樣本', '持照人', '外交護照', '公務護照',
            '日本國', '旅券', '本籍', '国籍', '発行', '發行'
        ]
        for line in lines:
            # Regex for pure Chinese characters, length 2-5
            if re.search(r'^[\u4e00-\u9fa5]{2,5}$', line.strip()):
                clean = line.strip()
                if clean not in ignore_list:
                    info['Name'] = clean
                    break
    
    # Fallback: use MRZ Name if visual failed
    if 'Name' not in info and 'MRZ Name' in info:
        info['Name'] = info['MRZ Name']

    return info

def standardize_to_checkin(raw_data):
    # Target: 姓名, 性別, 生日(YYYY/MM/DD), 國籍, 身份證/護照號碼, 地址
    final = {
        "姓名": raw_data.get('Name', raw_data.get('MRZ Name', '')),
        "行動電話": "", # OCR cannot get
        "E-mail": "",
        "性別": raw_data.get('Gender', ''),
        "電話": "",
        "生日": raw_data.get('Birthday', ''),
        "國籍": raw_data.get('Nationality', ''),
        "身份證/護照號碼": raw_data.get('ID Number', raw_data.get('Passport Number', '')),
        "地址": raw_data.get('Address', '')
    }
    
    # Cleanups
    if final["姓名"]: final["姓名"] = final["姓名"].strip().replace(" ", "")
    
    return final

if __name__ == "__main__":
    pass
