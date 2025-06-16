from django.core.management.base import BaseCommand
from student.models import RoomChangeRequest
from django.db.models import Count, Max

class Command(BaseCommand):
    help = 'Removes duplicate room change requests, keeping the most recent one for each student and booking'

    def handle(self, *args, **options):
        self.stdout.write("Starting cleanup of duplicate room change requests...")
        
        # Group by student, current_booking, requested_hostel, requested_room_type, and reason to find duplicates
        duplicates = (
            RoomChangeRequest.objects.values('student', 'current_booking', 'requested_hostel', 'requested_room_type', 'reason')
            .annotate(count=Count('id'), max_id=Max('id'))
            .filter(count__gt=1)
        )
        
        total_duplicates = 0
        deleted_count = 0
        
        for duplicate in duplicates:
            student_id = duplicate['student']
            booking_id = duplicate['current_booking']
            max_id = duplicate['max_id']
            total_duplicates += duplicate['count'] - 1
            
            # Delete all but the most recent request (max_id)
            deleted, _ = RoomChangeRequest.objects.filter(
                student_id=student_id,
                current_booking_id=booking_id,
                requested_hostel=duplicate['requested_hostel'],
                requested_room_type=duplicate['requested_room_type'],
                reason=duplicate['reason']
            ).exclude(id=max_id).delete()
            
            deleted_count += deleted
            self.stdout.write(f"Removed {deleted} duplicate(s) for student {student_id} and booking {booking_id} with room type {duplicate['requested_room_type']}")
        
        self.stdout.write(self.style.SUCCESS(f"Cleanup complete. Removed {deleted_count} duplicate room change requests out of {total_duplicates} identified."))
