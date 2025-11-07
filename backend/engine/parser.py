"""
Ericsson PM XML Parser
Parses Ericsson ENM PM counter XML files and extracts KPI measurements.
"""
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
from datetime import datetime
import re


# Ericsson PM counter mappings
COUNTER_MAPPINGS = {
    "1": "RRC_Setup_Success_Rate",
    "2": "ERAB_Setup_Success_Rate",
    "3": "PRB_Utilization_Avg",
    "4": "PRB_Utilization_P95",
    "5": "SINR_Avg",
    "6": "SINR_P10",
    "7": "BLER_P95",
    "8": "Paging_Success_Rate",
    "9": "S1_Setup_Failure_Rate",
    "10": "RRC_Connections",
    "11": "ERAB_Connections",
    "12": "Downlink_Throughput",
    "13": "Uplink_Throughput",
    "14": "Handover_Success_Rate",
    "15": "Cell_Availability",
}


def parse_ericsson_pm_xml(xml_content: bytes) -> List[Dict[str, Any]]:
    """
    Parse Ericsson PM XML content and extract KPI measurements.
    
    Args:
        xml_content: Raw XML bytes from decompressed .xml.gz file
    
    Returns:
        List of KPI measurement dictionaries with keys:
        - timestamp: ISO format datetime string
        - site: Site identifier (eNodeB ID or cell name)
        - kpi: KPI name
        - value: Numeric KPI value
    """
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        raise ValueError(f"Invalid XML format: {str(e)}")
    
    kpi_data = []
    
    # Initialize default timestamp
    default_timestamp = datetime.now().isoformat()
    
    # Strategy 1: Parse namespace-based mdc structure (Ericsson ENM format with namespaces)
    # Check for es:mdc or mdc root element
    root_tag = root.tag.split('}')[-1] if '}' in root.tag else root.tag  # Remove namespace prefix
    if root_tag == "mdc":
        kpi_data = parse_mdc_structure(root, default_timestamp)
        if kpi_data:
            return kpi_data
    
    # Strategy 2: Parse measCollecFile structure (Ericsson ENM format)
    # Check if root is measCollecFile or if it contains measCollecFile
    if root.tag == "measCollecFile" or root.find(".//measCollecFile") is not None:
        kpi_data = parse_meas_collec_file(root, default_timestamp)
        if kpi_data:
            return kpi_data
    
    # Strategy 3: Standard Ericsson PM structure: <pmContainer> -> <measInfo> -> <measValue>
    for pm_container in root.findall(".//pmContainer"):
        # Extract timestamp
        begin_time_elem = pm_container.find(".//beginTime")
        timestamp = None
        if begin_time_elem is not None:
            timestamp_str = begin_time_elem.text
            if timestamp_str:
                try:
                    # Parse Ericsson timestamp format (typically ISO 8601 or custom)
                    timestamp = parse_timestamp(timestamp_str)
                except:
                    timestamp = datetime.now().isoformat()
        
        if not timestamp:
            timestamp = datetime.now().isoformat()
        
        # Extract site/cell identifier
        site_id = None
        for elem in pm_container.iter():
            # Look for common site identifier attributes
            if "dn" in elem.attrib:
                dn = elem.attrib["dn"]
                # Extract eNodeB ID or cell name from DN
                site_match = re.search(r'eNodeBId=(\d+)|cellName=([^,]+)', dn)
                if site_match:
                    site_id = site_match.group(1) or site_match.group(2)
                    break
        
        if not site_id:
            # Try to find in other common locations
            local_dn = pm_container.find(".//localDn")
            if local_dn is not None and local_dn.text:
                site_match = re.search(r'eNodeBId=(\d+)|cellName=([^,]+)', local_dn.text)
                if site_match:
                    site_id = site_match.group(1) or site_match.group(2)
        
        if not site_id:
            site_id = "UNKNOWN"
        
        # Extract measurement information
        for meas_info in pm_container.findall(".//measInfo"):
            meas_type_elem = meas_info.find(".//measType")
            if meas_type_elem is None:
                continue
            
            # Get counter ID from p attribute or text
            counter_id = meas_type_elem.attrib.get("p", meas_type_elem.text)
            kpi_name = COUNTER_MAPPINGS.get(str(counter_id), f"Counter_{counter_id}")
            
            # Extract measurement values
            for meas_value in meas_info.findall(".//measValue"):
                # Get value from <r> elements
                for r_elem in meas_value.findall(".//r"):
                    value_str = r_elem.text
                    if value_str:
                        try:
                            value = float(value_str)
                            kpi_data.append({
                                "timestamp": timestamp,
                                "site": site_id,
                                "kpi": kpi_name,
                                "value": value
                            })
                        except ValueError:
                            continue
    
    # Strategy 4: If no data found with standard structure, try alternative parsing
    if not kpi_data:
        kpi_data = parse_alternative_structure(root, default_timestamp)
    
    # Strategy 5: Try to find measurements in any structure
    if not kpi_data:
        kpi_data = parse_flexible_structure(root, default_timestamp)
    
    return kpi_data


def parse_alternative_structure(root: ET.Element, default_timestamp: str) -> List[Dict[str, Any]]:
    """Alternative parsing method for different XML structures"""
    kpi_data = []
    
    # Look for any measurement-like structures
    for elem in root.iter():
        if elem.tag in ["measValue", "measurement", "counter"]:
            # Try to extract KPI name and value
            kpi_name = elem.attrib.get("name") or elem.attrib.get("type") or elem.attrib.get("id")
            if not kpi_name:
                # Try to get from child elements
                name_elem = elem.find(".//name") or elem.find(".//measType")
                if name_elem is not None:
                    kpi_name = name_elem.text or name_elem.attrib.get("p") or name_elem.attrib.get("name")
            
            # Try to extract site ID from parent elements
            site_id = extract_site_from_element(elem)
            
            value_elem = elem.find(".//value") or elem.find(".//r") or elem.find("value")
            if value_elem is not None and value_elem.text:
                try:
                    value = float(value_elem.text)
                    # Try to map counter ID to KPI name
                    if kpi_name and kpi_name.isdigit():
                        kpi_name = COUNTER_MAPPINGS.get(kpi_name, f"Counter_{kpi_name}")
                    elif not kpi_name:
                        kpi_name = "Unknown_KPI"
                    
                    kpi_data.append({
                        "timestamp": default_timestamp,
                        "site": site_id,
                        "kpi": kpi_name,
                        "value": value
                    })
                except ValueError:
                    continue
    
    return kpi_data


def parse_flexible_structure(root: ET.Element, default_timestamp: str) -> List[Dict[str, Any]]:
    """Flexible parsing that looks for any numeric values in the XML"""
    kpi_data = []
    
    # Look for measType elements anywhere in the tree
    for meas_type in root.findall(".//measType"):
        # Get counter ID
        counter_id = meas_type.attrib.get("p") or meas_type.text
        if not counter_id:
            continue
        
        kpi_name = COUNTER_MAPPINGS.get(str(counter_id), f"Counter_{counter_id}")
        
        # Find parent measInfo to get related measurements
        # Walk up the tree to find measInfo parent
        meas_info = None
        for parent in root.iter():
            if meas_type in list(parent.iter()):
                # Check if this parent is a measInfo or contains measInfo
                if parent.tag == "measInfo":
                    meas_info = parent
                    break
                # Check if parent contains measInfo
                meas_info_elem = parent.find(".//measInfo")
                if meas_info_elem is not None:
                    meas_info = meas_info_elem
                    break
        
        if meas_info is not None:
            # Extract site ID
            site_id = extract_site_from_element(meas_info)
            
            # Find measurement values
            for meas_value in meas_info.findall(".//measValue"):
                for r_elem in meas_value.findall(".//r"):
                    if r_elem.text:
                        try:
                            value = float(r_elem.text)
                            kpi_data.append({
                                "timestamp": default_timestamp,
                                "site": site_id,
                                "kpi": kpi_name,
                                "value": value
                            })
                        except ValueError:
                            continue
    
    return kpi_data


def extract_site_from_element(elem: ET.Element) -> str:
    """Extract site identifier from an element or its parents"""
    # Walk up the tree to find site information
    current = elem
    for _ in range(10):  # Limit depth to avoid infinite loops
        if current is None:
            break
        
        # Check for DN attribute
        if "dn" in current.attrib:
            dn = current.attrib["dn"]
            site_match = re.search(r'eNodeBId=(\d+)|cellName=([^,]+)|ManagedElement=([^,]+)', dn)
            if site_match:
                return site_match.group(1) or site_match.group(2) or site_match.group(3) or "UNKNOWN"
        
        # Check for localDn
        local_dn_elem = current.find(".//localDn")
        if local_dn_elem is not None and local_dn_elem.text:
            site_match = re.search(r'eNodeBId=(\d+)|cellName=([^,]+)|ManagedElement=([^,]+)', local_dn_elem.text)
            if site_match:
                return site_match.group(1) or site_match.group(2) or site_match.group(3) or "UNKNOWN"
        
        # Check for eNodeBId or cellName in attributes
        if "eNodeBId" in current.attrib:
            return current.attrib["eNodeBId"]
        if "cellName" in current.attrib:
            return current.attrib["cellName"]
        
        # Move to parent by searching for elements that contain this one
        # This is a simplified approach - in practice, we'd need to track parent during iteration
        parent_found = False
        for potential_parent in root.iter():
            if current in list(potential_parent.iter()):
                current = potential_parent
                parent_found = True
                break
        if not parent_found:
            break
    
    return "UNKNOWN"


def parse_meas_collec_file(root: ET.Element, default_timestamp: str) -> List[Dict[str, Any]]:
    """Parse Ericsson measCollecFile XML structure"""
    kpi_data = []
    
    # Extract file header timestamp
    file_header = root.find(".//fileHeader")
    file_begin_time = default_timestamp
    if file_header is not None:
        begin_time_attr = file_header.attrib.get("beginTime")
        if begin_time_attr:
            file_begin_time = parse_timestamp(begin_time_attr)
    
    # Extract managed element (site ID)
    managed_element = root.find(".//managedElement")
    default_site_id = "UNKNOWN"
    if managed_element is not None:
        local_dn = managed_element.attrib.get("localDn")
        if local_dn:
            # Extract site ID from localDn (e.g., "ERBS-41001")
            default_site_id = local_dn
    
    # Process each measInfo block
    for meas_info in root.findall(".//measInfo"):
        # Extract measurement types and create mapping
        meas_types = {}
        for meas_type in meas_info.findall("measType"):  # Direct children of measInfo
            p_attr = meas_type.attrib.get("p")
            type_name = meas_type.text
            if p_attr:
                if type_name and type_name.strip():
                    meas_types[p_attr] = type_name.strip()
                else:
                    # If no text, use the p attribute as fallback
                    meas_types[p_attr] = f"Counter_{p_attr}"
        
        # Process each measValue
        for meas_value in meas_info.findall(".//measValue"):
            # Extract timestamp from measValue
            begin_time = meas_value.attrib.get("beginTime") or file_begin_time
            if begin_time:
                timestamp = parse_timestamp(begin_time)
            else:
                timestamp = default_timestamp
            
            # Extract site/cell ID from measObjLdn
            meas_obj_ldn = meas_value.attrib.get("measObjLdn", "")
            site_id = default_site_id
            if meas_obj_ldn:
                # Extract cell name from measObjLdn (e.g., "EUtranCellFDD=Cell-1")
                cell_match = re.search(r'=([^,]+)', meas_obj_ldn)
                if cell_match:
                    site_id = f"{default_site_id}_{cell_match.group(1)}"
                else:
                    site_id = meas_obj_ldn
            
            # Extract measurement values
            for r_elem in meas_value.findall(".//r"):
                p_attr = r_elem.attrib.get("p")
                value_str = r_elem.text
                
                if p_attr and value_str:
                    try:
                        value = float(value_str)
                        # Get KPI name from measTypes mapping
                        kpi_name = meas_types.get(p_attr)
                        
                        if not kpi_name:
                            # Fallback: try to map numeric ID to known KPIs
                            kpi_name = COUNTER_MAPPINGS.get(p_attr, f"Counter_{p_attr}")
                        else:
                            # Map Ericsson PM counter names to our standard names
                            kpi_name = map_ericsson_counter_name(kpi_name)
                        
                        kpi_data.append({
                            "timestamp": timestamp,
                            "site": site_id,
                            "kpi": kpi_name,
                            "value": value
                        })
                    except ValueError:
                        continue
    
    return kpi_data


def parse_mdc_structure(root: ET.Element, default_timestamp: str) -> List[Dict[str, Any]]:
    """Parse Ericsson mdc XML structure with namespaces"""
    kpi_data = []
    
    # Define namespace - Ericsson typically uses this namespace
    ns_uri = None
    if '}' in root.tag:
        # Extract namespace from root tag
        ns_uri = root.tag.split('}')[0].strip('{')
    
    # Extract managed element (site ID)
    managed_element = None
    if ns_uri:
        managed_element = root.find(f".//{{{ns_uri}}}managedElement")
    if managed_element is None:
        # Try without namespace
        managed_element = root.find(".//managedElement")
    
    default_site_id = "UNKNOWN"
    if managed_element is not None:
        site_id = managed_element.attrib.get("id") or managed_element.attrib.get("userLabel")
        if site_id:
            default_site_id = site_id
    
    # Extract timestamp from granPeriod
    gran_period = None
    if ns_uri:
        gran_period = root.find(f".//{{{ns_uri}}}granPeriod")
    if gran_period is None:
        gran_period = root.find(".//granPeriod")
    
    file_timestamp = default_timestamp
    if gran_period is not None:
        end_time = gran_period.attrib.get("endTime")
        if end_time:
            file_timestamp = parse_timestamp(end_time)
    
    # Process each measInfo block
    meas_info_elements = []
    if ns_uri:
        meas_info_elements = root.findall(f".//{{{ns_uri}}}measInfo")
    if not meas_info_elements:
        # Try without namespace
        meas_info_elements = root.findall(".//measInfo")
    
    for meas_info in meas_info_elements:
        # Extract measurement types and create mapping
        meas_types = {}
        meas_type_elements = []
        if ns_uri:
            meas_type_elements = meas_info.findall(f"{{{ns_uri}}}measType")
        if not meas_type_elements:
            meas_type_elements = meas_info.findall("measType")
        
        for meas_type in meas_type_elements:
            p_attr = meas_type.attrib.get("p")
            type_name = meas_type.text
            if p_attr:
                if type_name and type_name.strip():
                    meas_types[p_attr] = type_name.strip()
                else:
                    meas_types[p_attr] = f"Counter_{p_attr}"
        
        # Process each measValue
        meas_value_elements = []
        if ns_uri:
            meas_value_elements = meas_info.findall(f"{{{ns_uri}}}measValue")
        if not meas_value_elements:
            meas_value_elements = meas_info.findall("measValue")
        
        for meas_value in meas_value_elements:
            # Extract timestamp (use granPeriod endTime or default)
            timestamp = file_timestamp
            
            # Extract site/cell ID from measObjLdn
            meas_obj_ldn = meas_value.attrib.get("measObjLdn", "")
            site_id = default_site_id
            if meas_obj_ldn:
                # Extract cell name from measObjLdn if present
                cell_match = re.search(r'=([^,]+)', meas_obj_ldn)
                if cell_match:
                    site_id = f"{default_site_id}_{cell_match.group(1)}"
                else:
                    site_id = meas_obj_ldn if meas_obj_ldn else default_site_id
            
            # Extract measurement values
            r_elements = []
            if ns_uri:
                r_elements = meas_value.findall(f"{{{ns_uri}}}r")
            if not r_elements:
                r_elements = meas_value.findall("r")
            
            for r_elem in r_elements:
                p_attr = r_elem.attrib.get("p")
                value_str = r_elem.text
                
                if p_attr and value_str:
                    try:
                        value = float(value_str)
                        # Get KPI name from measTypes mapping
                        kpi_name = meas_types.get(p_attr)
                        
                        if not kpi_name:
                            # Fallback: try to map numeric ID to known KPIs
                            kpi_name = COUNTER_MAPPINGS.get(p_attr, f"Counter_{p_attr}")
                        else:
                            # Map Ericsson PM counter names to our standard names
                            kpi_name = map_ericsson_counter_name(kpi_name)
                        
                        kpi_data.append({
                            "timestamp": timestamp,
                            "site": site_id,
                            "kpi": kpi_name,
                            "value": value
                        })
                    except ValueError:
                        continue
    
    return kpi_data


def map_ericsson_counter_name(counter_name: str) -> str:
    """Map Ericsson PM counter names to standard KPI names"""
    # Ericsson counter name mappings
    ericsson_mappings = {
        "pmRrcConnEstabAtt": "RRC_Setup_Attempts",
        "pmRrcConnEstabSucc": "RRC_Setup_Success",
        "pmPdcpVolDlDrb": "Downlink_Throughput",
        "pmPrbUsedDlAvg": "PRB_Utilization_Avg",
        "pmPrbUsedDl": "PRB_Utilization_Avg",
        "pmSinrPusch": "SINR_PUSCH",
        "pmBlerDl": "BLER_DL",
        "pmRrcConnEstab": "RRC_Setup_Success_Rate",
        "pmErabEstabAtt": "ERAB_Setup_Attempts",
        "pmErabEstabSucc": "ERAB_Setup_Success",
        "pmErabEstab": "ERAB_Setup_Success_Rate",
        "pmSinrAvg": "SINR_Avg",
        "pmSinrP10": "SINR_P10",
        "pmBlerP95": "BLER_P95",
        "pmPagingSucc": "Paging_Success_Rate",
        "pmS1EstabFail": "S1_Setup_Failure_Rate",
        "pmCellAvail": "Cell_Availability",
    }
    
    # Direct mapping
    if counter_name in ericsson_mappings:
        return ericsson_mappings[counter_name]
    
    # Try case-insensitive match
    counter_lower = counter_name.lower()
    for ericsson_name, standard_name in ericsson_mappings.items():
        if ericsson_name.lower() == counter_lower:
            return standard_name
    
    # Return original name if no mapping found
    return counter_name


def parse_timestamp(timestamp_str: str) -> str:
    """Parse various timestamp formats to ISO format"""
    if not timestamp_str:
        return datetime.now().isoformat()
    
    # Remove timezone Z and convert to ISO format
    timestamp_str = timestamp_str.strip()
    if timestamp_str.endswith('Z'):
        timestamp_str = timestamp_str[:-1]
    
    # Try common formats
    formats = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(timestamp_str, fmt)
            return dt.isoformat()
        except ValueError:
            continue
    
    # If no format matches, return as-is or current time
    return datetime.now().isoformat()

