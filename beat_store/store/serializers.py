from rest_framework import serializers
from .models import Song, Genre, User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'balance']

class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ['id', 'name']

class SongSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    genre = GenreSerializer(read_only=True)
    total_likes = serializers.IntegerField(read_only=True)

    class Meta:
        model = Song
        fields = ['id', 'title', 'path', 'cover', 'author', 'genre', 'price', 'total_plays', 'total_likes', 'created_at']