"""Check AM/PM parsing issue."""
from datetime import datetime

EXPECTED_DT_FORMATS = ['%d-%m-%y %H:%M %p', '%d-%m-%y %H:%M']

# Test the problematic dates
dates = [
    '31-08-25 11:14 PM',
    '31-08-25 11:45 AM',
    '31-08-25 11:46 AM',
    '31-08-25 11:45',  # Without AM/PM
    '31-08-25 11:46'   # Without AM/PM
]

for date_str in dates:
    for fmt in EXPECTED_DT_FORMATS:
        try:
            parsed = datetime.strptime(date_str, fmt)
            print(f"{date_str:25} -> {parsed} (format: {fmt})")
            break
        except (ValueError, TypeError):
            continue
