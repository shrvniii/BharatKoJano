import csv

def build_rankings_csv(submissions, file_object):
    """
    Writes all submissions (evaluated and errored) with details into a CSV file object.
    Supports Excel UTF-8 encoding.
    """
    writer = csv.writer(file_object)
    
    # Headers
    writer.writerow([
        'S.No.',
        'School Code',
        'School Name',
        'Full Roll Number',
        'Student Name',
        'Category',
        'Question Paper Set',
        'Marks Obtained',
        'Percentage',
        'Correct Answers',
        'Wrong Answers',
        'Unanswered Questions',
        'Confidence Score',
        'Scan Status',
        'Scan Timestamp',
        'Operator'
    ])
    
    # Data Rows
    for idx, s in enumerate(submissions):
        p = s.participant
        r = getattr(s, 'result', None)
        
        # School details
        school_code = p.school.code if (p and p.school) else '—'
        if school_code != '—':
            school_code = f'="{school_code}"'
        school_name = p.school.name if (p and p.school) else '—'
        
        # Participant details
        roll_number = p.roll_number if p else '—'
        if roll_number != '—':
            roll_number = f'="{roll_number}"'
        student_name = p.student_name if (p and p.student_name) else '—'
        category = p.get_group_display() if p else '—'
        paper_set = p.get_paper_set_display() if p else '—'
        
        # Result details
        if r:
            marks_obtained = r.score
            percentage = f"{r.percentage}%"
            correct = r.score
            unanswered = r.unanswered_count
            wrong = 50 - r.score - r.unanswered_count - r.multi_marked_count
            confidence = f"{r.confidence_score}%"
        else:
            marks_obtained = '—'
            percentage = '—'
            correct = '—'
            wrong = '—'
            unanswered = '—'
            confidence = '—'
            
        status = s.get_status_display()
        timestamp = s.uploaded_at.strftime('%Y-%m-%d %H:%M:%S')
        operator = s.operator.username if s.operator else 'System'
        
        writer.writerow([
            idx + 1,
            school_code,
            school_name,
            roll_number,
            student_name,
            category,
            paper_set,
            marks_obtained,
            percentage,
            correct,
            wrong,
            unanswered,
            confidence,
            status,
            timestamp,
            operator
        ])
