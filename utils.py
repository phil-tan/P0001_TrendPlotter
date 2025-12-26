"""
Utility functions for Trend Plotter
"""

import re
import pandas as pd
from dateutil import parser as date_parser


def detect_date_format(date_series):
    """
    Auto-detect if dates are in day-first or month-first format.
    Uses chronological ordering: assumes timestamps should be in order and
    checks which format produces an ordered sequence.
    Returns True if day-first produces ordered timestamps, False if month-first does.
    """
    # Sample non-null values
    sample = date_series.dropna().head(50).astype(str)
    if len(sample) < 2:
        return False
    
    dayfirst_result = []
    monthfirst_result = []
    parse_success = {"dayfirst": 0, "monthfirst": 0}
    
    # Try parsing with both formats
    for date_str in sample:
        try:
            parsed_df = date_parser.parse(date_str, dayfirst=True, fuzzy=False)
            dayfirst_result.append(parsed_df)
            parse_success["dayfirst"] += 1
        except:
            dayfirst_result.append(None)
        
        try:
            parsed_mf = date_parser.parse(date_str, dayfirst=False, fuzzy=False)
            monthfirst_result.append(parsed_mf)
            parse_success["monthfirst"] += 1
        except:
            monthfirst_result.append(None)
    
    # Filter out None values for ordering checks
    dayfirst_valid = [d for d in dayfirst_result if d is not None]
    monthfirst_valid = [d for d in monthfirst_result if d is not None]
    
    if not dayfirst_valid or not monthfirst_valid:
        return False
    
    # Check if dates are in chronological order (allowing equal consecutive values)
    def is_ordered(date_list):
        for i in range(len(date_list) - 1):
            if date_list[i] > date_list[i + 1]:  # Out of order if current > next
                return False
        return True
    
    dayfirst_ordered = is_ordered(dayfirst_valid)
    monthfirst_ordered = is_ordered(monthfirst_valid)
    
    # If only one format produces ordered dates, use that
    if dayfirst_ordered and not monthfirst_ordered:
        return True
    elif monthfirst_ordered and not dayfirst_ordered:
        return False
    
    # If both or neither are ordered, fall back to detecting impossible values
    dayfirst_evidence = 0
    monthfirst_evidence = 0
    
    for date_str in sample:
        numbers = re.findall(r'\d+', date_str)
        
        if len(numbers) >= 2:
            first_val = int(numbers[0])
            second_val = int(numbers[1])
            
            if first_val > 12:
                dayfirst_evidence += 2
            elif second_val > 12:
                monthfirst_evidence += 2
            elif first_val > second_val:
                dayfirst_evidence += 1
    
    return dayfirst_evidence > monthfirst_evidence


def is_valid_time_series(date_series):
    """
    Validates if the series contains proper datetime values.
    Must have at least 80% non-null values that can be parsed as dates.
    """
    if len(date_series) == 0:
        return False
    
    non_null_count = date_series.dropna().shape[0]
    if non_null_count < len(date_series) * 0.8:  # At least 80% non-null
        return False
    
    # Try to parse a sample
    sample = date_series.dropna().head(5).astype(str)
    valid_dates = 0
    
    for date_str in sample:
        try:
            parsed = date_parser.parse(date_str, fuzzy=False)  # fuzzy=False ensures strict parsing
            valid_dates += 1
        except:
            pass
    
    # At least 80% of sample must be valid dates
    return (valid_dates / len(sample)) >= 0.8 if len(sample) > 0 else False
