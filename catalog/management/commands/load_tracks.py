from django.core.management.base import BaseCommand
from django.db import transaction
import csv
from datetime import datetime
from artist.models import Artist
from catalog.models import Track, Genre
from django.core.files import File


class Command(BaseCommand):
    help = 'Import tracks from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='The CSV file to import')

    @transaction.atomic
    def handle(self, *args, **kwargs):
        csv_file_path = kwargs['csv_file']
        
        with open(csv_file_path, 'r', encoding='utf-8') as csv_file:
            reader = csv.DictReader(csv_file)
            
            for row in reader:
                if row['SONG ISRC CODE']:
                    artist_name = row['ARTIST NAME']
                    artist, _ = Artist.objects.get_or_create(
                        name=artist_name,
                        defaults={'hometown': row['MAIN ARTIST HOMETOWN'], 'spotify_url': row['YOUR SPOTIFY ARTIST PROFILE URL']}
                    )

                    song_length = None

                    LANGS = {
                        'Spanish': 'ES',
                        'English': 'EN',
                    }
                    language = LANGS.get(row['LANGUAGE(S)'], '')
                    try:
                        bpm = int(row['BPM']) if row['BPM'] else None
                    except ValueError:
                        bpm = None
                    
                    try:
                        duration = sum(x * int(t) for x, t in zip([60, 1], row['SONG LENGTH'].split(":"))) if row['SONG LENGTH'] else None
                    except ValueError:
                        duration = None

                    track, created = Track.objects.get_or_create(
                        isrc=row['SONG ISRC CODE'].strip(),
                        defaults={
                            'artist': artist,
                            'name': row['SONG NAME'].strip(),
                            # Assuming duration is provided in minutes:seconds format in the CSV
                            'duration': duration,
                            'released': datetime.strptime(row['Submitted on'], '%Y/%m/%d').date() if row['Submitted on'] else None,
                            'is_cover': row['IS IT A COVER OF SOMEONE ELSE\'S SONG?'].strip().lower() == 'yes' if row['IS IT A COVER OF SOMEONE ELSE\'S SONG?'] else False,
                            'is_remix': row['IS IT A REMIX?'].strip().lower() == 'yes' if row['IS IT A REMIX?'] else False,
                            'is_instrumental': row['IS IT AN INSTRUMENTAL?'].strip().lower() == 'yes' if row['IS IT AN INSTRUMENTAL?'] else False,
                            'is_explicit': row['EXPLICIT LYRICS?'].strip().lower() == 'yes' if row['EXPLICIT LYRICS?'] else False,
                            #'record_type': Track.RecordType.STUDIO if row['HOW WAS IT RECORDED?'].strip().lower() == 'studio' else None,
                            'bpm': bpm,
                            'language': language,
                            'lyrics': row['LYRICS'].strip() if row['LYRICS'] else '',
                        }
                    )
                    
                    if created:
                        # Handle file uploads if needed, e.g.:
                        #with open(row['UPLOAD WAV FILE // MUST MATCH NAME OF SONG EXACTLY'], 'rb') as f:
                        #    track.file_wav.save(row['UPLOAD WAV FILE // MUST MATCH NAME OF SONG EXACTLY'], File(f))
                        # Repeat for other file fields
                        
                        # Add genres
                        genres = [row['GENRE 1'], row['GENRE 2'], row['GENRE 3']]
                        for genre_name in genres:
                            if genre_name:
                                genre, _ = Genre.objects.get_or_create(name=genre_name)
                                track.genres.add(genre)

                    self.stdout.write(self.style.SUCCESS(f'Successfully imported "{track.name}" by {artist.name}'))
