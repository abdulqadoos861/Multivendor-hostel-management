from django.core.management.base import BaseCommand
from django.db.models import Count, Max
from coustom_admin.models import BookingRequest
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Cleans up duplicate booking requests by keeping the most recent one for each student and status combination.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Starting cleanup of duplicate booking requests...'))
        logger.info('Starting cleanup of duplicate booking requests.')

        # Identify duplicates based on student_id and status
        duplicates = (BookingRequest.objects.values('student_id', 'status')
                      .annotate(count=Count('id'), latest_id=Max('id'))
                      .filter(count__gt=1))

        total_duplicates_found = len(duplicates)
        total_records_deleted = 0

        if total_duplicates_found == 0:
            self.stdout.write(self.style.SUCCESS('No duplicate booking requests found.'))
            logger.info('No duplicate booking requests found.')
            return

        self.stdout.write(f'Found {total_duplicates_found} sets of duplicate booking requests.')
        logger.info(f'Found {total_duplicates_found} sets of duplicate booking requests.')

        for duplicate in duplicates:
            student_id = duplicate['student_id']
            status = duplicate['status']
            latest_id = duplicate['latest_id']
            count = duplicate['count']

            self.stdout.write(f'Processing duplicates for Student ID: {student_id}, Status: {status}, Total: {count}')
            logger.info(f'Processing duplicates for Student ID: {student_id}, Status: {status}, Total: {count}')

            # Get all records for this student and status, excluding the most recent one
            duplicate_records = BookingRequest.objects.filter(
                student_id=student_id,
                status=status
            ).exclude(id=latest_id).order_by('request_date')

            for record in duplicate_records:
                self.stdout.write(f'Deleting duplicate Booking ID: {record.id}, Request Date: {record.request_date}')
                logger.info(f'Deleting duplicate Booking ID: {record.id}, Request Date: {record.request_date}')
                record.delete()
                total_records_deleted += 1

        self.stdout.write(self.style.SUCCESS(f'Cleanup completed. Deleted {total_records_deleted} duplicate records out of {total_duplicates_found} sets of duplicates.'))
        logger.info(f'Cleanup completed. Deleted {total_records_deleted} duplicate records out of {total_duplicates_found} sets of duplicates.')
