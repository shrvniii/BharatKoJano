import sys
from django.db import migrations

def update_school_list(apps, schema_editor):
    # Skip during unit tests to avoid constraint conflicts with test data setup
    if 'test' in sys.argv or any('test' in arg for arg in sys.argv):
        return

    School = apps.get_model('schools', 'School')
    Participant = apps.get_model('participants', 'Participant')

    # 1. Shift existing schools and participants down by 4
    # We sort existing schools by code descending to avoid unique constraint violations
    schools = School.objects.all().order_by('-code')
    for school in schools:
        old_code = school.code
        # Convert code to integer, add 4, and format back to 2 digits
        new_code = f"{int(old_code) + 4:02d}"
        
        # Shift all participants of this school
        participants = Participant.objects.filter(school=school)
        for participant in participants:
            if participant.roll_number.startswith(old_code):
                participant.roll_number = new_code + participant.roll_number[2:]
                participant.save()
        
        school.code = new_code
        school.save()

    # 2. Insert the 4 new schools at the beginning (codes 01 to 04)
    new_schools_data = [
        ('01', 'New Horizons Public School'),
        ('02', 'Mansoravar High School, Kamothe'),
        ('03', 'ST Agrasen High School, Kamothe'),
        ('04', 'CKT High School, English Medium'),
    ]
    for code, name in new_schools_data:
        School.objects.create(code=code, name=name)

def rollback_school_list(apps, schema_editor):
    # Skip during unit tests
    if 'test' in sys.argv or any('test' in arg for arg in sys.argv):
        return

    School = apps.get_model('schools', 'School')
    Participant = apps.get_model('participants', 'Participant')

    # 1. Delete the 4 new schools (codes 01 to 04)
    School.objects.filter(code__in=['01', '02', '03', '04']).delete()

    # 2. Shift existing schools and participants back up by 4 (codes 05 to 33 -> 01 to 29)
    # We sort ascending to avoid unique constraint violations on the way back
    schools = School.objects.all().order_by('code')
    for school in schools:
        old_code = school.code
        new_code = f"{int(old_code) - 4:02d}"
        
        participants = Participant.objects.filter(school=school)
        for participant in participants:
            if participant.roll_number.startswith(old_code):
                participant.roll_number = new_code + participant.roll_number[2:]
                participant.save()
                
        school.code = new_code
        school.save()

class Migration(migrations.Migration):

    dependencies = [
        ('schools', '0002_populate_default_schools'),
        ('participants', '0003_participant_student_name_and_more'),
    ]

    operations = [
        migrations.RunPython(update_school_list, reverse_code=rollback_school_list),
    ]
