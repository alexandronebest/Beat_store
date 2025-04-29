from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Song, Genre
from .serializers import SongSerializer, GenreSerializer

class SongViewSet(viewsets.ModelViewSet):
    queryset = Song.objects.all()
    serializer_class = SongSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        genre_id = self.request.query_params.get('genre')
        search_query = self.request.query_params.get('search')
        if genre_id:
            queryset = queryset.filter(genre_id=genre_id)
        if search_query:
            queryset = queryset.filter(title__icontains=search_query) | queryset.filter(author__username__icontains=search_query)
        return queryset.order_by('-created_at')

class GenreViewSet(viewsets.ModelViewSet):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    permission_classes = [IsAuthenticated]