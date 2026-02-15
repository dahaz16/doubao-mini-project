import sys
import os
import datetime
import json
from decimal import Decimal

# Add backend directory to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DateTimeEncoder, self).default(obj)

try:
    from backend.interview_detail_service import get_user_interview_details
    
    user_id = 'f5577e07-00b5-4394-836b-cd145a453a69'
    
    # Calculate today's start and end time (UTC approx or just wide range)
    # The feedback was created at 2026-02-14 02:44:14 UTC
    start_time = datetime.datetime.fromisoformat("2026-02-14T00:00:00+00:00")
    end_time = datetime.datetime.fromisoformat("2026-02-14T23:59:59+00:00")
    
    print(f"Querying interview details for user: {user_id}")
    print(f"Time range: {start_time} - {end_time}")
    
    result = get_user_interview_details(
        user_id=user_id,
        data_types=["user", "intv_output", "stn_llm", "dir_llm", "feedback"],
        start_time=start_time,
        end_time=end_time,
        page=1,
        page_size=50
    )
    
    print(f"Total records found: {result['total']}")
    
    feedback_found = False
    for record in result['records']:
        if record['data_type'] == 'feedback':
            feedback_found = True
            print("\n✅ Found Feedback Record:")
            print(json.dumps(record, indent=2, cls=DateTimeEncoder, ensure_ascii=False))
            
    if not feedback_found:
        print("\n❌ No feedback records found in the result.")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
