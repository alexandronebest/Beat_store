const Player = (function () {
    let audioPlayer,
        audioSource,
        currentSongDisplay,
        likeButtonPlayer,
        playPauseButton,
        volumeSlider,
        progressBar,
        prevButton,
        nextButton,
        muteButton,
        currentTimeDisplay,
        totalTimeDisplay,
        songPriceElement;

    let currentSongId = null;
    let playlist = [];
    let currentIndex = -1;
    let previousVolume = 0.5;
    let hasPlayed = false;

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

    function init(songsData = []) {
        updatePlaylist(songsData);

        audioPlayer = document.getElementById('audio-player');
        audioSource = document.getElementById('audio-source');
        currentSongDisplay = document.getElementById('current-song');
        likeButtonPlayer = document.getElementById('like-button-player');
        playPauseButton = document.getElementById('play-pause-button');
        volumeSlider = document.getElementById('volume-slider');
        progressBar = document.getElementById('progress-bar');
        prevButton = document.getElementById('prev-button');
        nextButton = document.getElementById('next-button');
        muteButton = document.getElementById('mute-button');
        currentTimeDisplay = document.getElementById('current-time');
        totalTimeDisplay = document.getElementById('total-time');
        songPriceElement = document.getElementById('song-price');

        if (!audioPlayer || !audioSource || !currentSongDisplay) {
            console.error('Необходимые элементы плеера не найдены');
            return;
        }

        audioPlayer.volume = parseFloat(localStorage.getItem('volume')) || 0.5;
        volumeSlider.value = audioPlayer.volume;
        setupEventListeners();
        restorePlayerState();
    }

    function updatePlaylist(songsData) {
        const newSongs = songsData.map(song => ({
            id: parseInt(song.id),
            url: song.path,
            title: song.title,
            author: song.author,
            likes: parseInt(song.total_likes) || 0,
            price: parseFloat(song.price) || 0,
            plays: parseInt(song.total_plays) || 0
        }));

        if (JSON.stringify(playlist) !== JSON.stringify(newSongs)) {
            playlist = newSongs;
            currentIndex = playlist.findIndex(song => song.id === currentSongId);
        }
    }

    function setupEventListeners() {
        document.querySelectorAll('.play-button').forEach(button => {
            button.removeEventListener('click', handlePlayClick);
            button.addEventListener('click', handlePlayClick);
        });

        document.querySelectorAll('.like-button').forEach(button => {
            button.removeEventListener('click', handleLikeClick);
            button.addEventListener('click', handleLikeClick);
        });

        audioPlayer.addEventListener('play', () => {
            updatePlayPauseIcon(true);
            updateAllPlayIcons(currentSongId, true);
            if (!hasPlayed && currentSongId) {
                incrementPlayCount(currentSongId);
                hasPlayed = true;
            }
            savePlayerState();
        });
        audioPlayer.addEventListener('pause', () => {
            updatePlayPauseIcon(false);
            updateAllPlayIcons(currentSongId, false);
            savePlayerState();
        });
        audioPlayer.addEventListener('timeupdate', updateProgress);
        audioPlayer.addEventListener('loadedmetadata', updateTimeDisplay);
        audioPlayer.addEventListener('ended', playNextSong);
        audioPlayer.addEventListener('error', handleAudioError);

        likeButtonPlayer.addEventListener('click', handlePlayerLikeClick);
        playPauseButton.addEventListener('click', togglePlayPause);
        prevButton.addEventListener('click', playPreviousSong);
        nextButton.addEventListener('click', playNextSong);
        volumeSlider.addEventListener('input', () => {
            audioPlayer.volume = parseFloat(volumeSlider.value);
            updateMuteIcon();
            localStorage.setItem('volume', audioPlayer.volume);
        });
        muteButton.addEventListener('click', toggleMute);
        progressBar.addEventListener('input', () => {
            audioPlayer.currentTime = progressBar.value * audioPlayer.duration;
            savePlayerState();
        });

        window.addEventListener('load', restorePlayerState);
        document.addEventListener('keydown', handleKeyboardControls);
    }

    function handlePlayClick() {
        const songId = parseInt(this.getAttribute('data-song-id'), 10);
        const songIndex = playlist.findIndex(song => song.id === songId);

        if (songIndex === -1) {
            console.error(`Песня с ID ${songId} не найдена в плейлисте`);
            return;
        }

        if (currentSongId === songId && !audioPlayer.paused) {
            togglePlayPause();
        } else {
            playSong(songIndex);
        }
    }

    function playSong(songIndex) {
        const song = playlist[songIndex];
        if (!song) return;

        resetPlayButtons();
        audioSource.src = song.url;
        audioPlayer.load();
        audioPlayer.play()
            .then(() => {
                currentSongId = song.id;
                currentIndex = songIndex;
                currentSongDisplay.textContent = `${song.title} - ${song.author || 'Неизвестен'}`;
                songPriceElement.textContent = `₽${song.price.toFixed(2)}`;
                songPriceElement.dataset.songId = song.id;
                likeButtonPlayer.dataset.likes = song.likes;
                updatePlayerLikeState(song.id);
                hasPlayed = false;
                updatePlayPauseIcon(true);
                updateAllPlayIcons(song.id, true);
                savePlayerState();
            })
            .catch(err => {
                console.error('Ошибка воспроизведения:', err);
                handleAudioError();
            });
    }

    function updateProgress() {
        if (!audioPlayer.duration) return;
        progressBar.value = audioPlayer.currentTime / audioPlayer.duration;
        currentTimeDisplay.textContent = formatTime(audioPlayer.currentTime);
        totalTimeDisplay.textContent = formatTime(audioPlayer.duration);
    }

    function updateTimeDisplay() {
        totalTimeDisplay.textContent = formatTime(audioPlayer.duration);
        currentTimeDisplay.textContent = formatTime(audioPlayer.currentTime);
    }

    function incrementPlayCount(songId) {
        fetch(`/play-song/${songId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'Content-Type': 'application/json',
            },
        })
            .then(response => response.ok ? response.json() : Promise.reject(response.status))
            .then(data => {
                const playCountElement = document.getElementById(`plays-count-${songId}`);
                if (playCountElement) playCountElement.innerHTML = `<i class="bi bi-play-fill"></i> ${data.total_plays}`;
                if (currentIndex !== -1) playlist[currentIndex].plays = data.total_plays;
            })
            .catch(error => console.error('Ошибка при увеличении счётчика:', error));
    }

    function playNextSong() {
        if (currentIndex < playlist.length - 1 && currentIndex !== -1) {
            playSong(currentIndex + 1);
        } else {
            handleSongEnd();
        }
    }

    function playPreviousSong() {
        if (currentIndex > 0 && currentIndex !== -1) {
            playSong(currentIndex - 1);
        }
    }

    function togglePlayPause() {
        if (!currentSongId) return;

        if (audioPlayer.paused) {
            audioPlayer.play()
                .then(() => {
                    updatePlayPauseIcon(true);
                    updateAllPlayIcons(currentSongId, true);
                })
                .catch(err => console.error('Ошибка воспроизведения:', err));
        } else {
            audioPlayer.pause();
            updatePlayPauseIcon(false);
            updateAllPlayIcons(currentSongId, false);
        }
        savePlayerState();
    }

    function toggleMute() {
        if (audioPlayer.volume > 0) {
            previousVolume = audioPlayer.volume;
            audioPlayer.volume = 0;
            volumeSlider.value = 0;
        } else {
            audioPlayer.volume = previousVolume;
            volumeSlider.value = previousVolume;
        }
        updateMuteIcon();
        localStorage.setItem('volume', audioPlayer.volume);
    }

    function updateMuteIcon() {
        const icon = muteButton.querySelector('i');
        icon.classList.toggle('bi-volume-mute-fill', audioPlayer.volume === 0);
        icon.classList.toggle('bi-volume-up-fill', audioPlayer.volume > 0);
    }

    function updatePlayPauseIcon(isPlaying) {
        const icon = playPauseButton.querySelector('i');
        icon.classList.toggle('bi-play-fill', !isPlaying);
        icon.classList.toggle('bi-pause-fill', isPlaying);
    }

    function updateAllPlayIcons(songId, isPlaying) {
        document.querySelectorAll(`.play-button[data-song-id="${songId}"] i`).forEach(icon => {
            icon.classList.toggle('bi-play-fill', !isPlaying);
            icon.classList.toggle('bi-pause-fill', isPlaying);
        });
    }

    function formatTime(seconds) {
        if (isNaN(seconds)) return '0:00';
        const minutes = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${minutes}:${secs < 10 ? '0' : ''}${secs}`;
    }

    function handleKeyboardControls(e) {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
        if (e.key === 'ArrowRight') playNextSong();
        if (e.key === 'ArrowLeft') playPreviousSong();
        if (e.key === ' ') {
            e.preventDefault();
            togglePlayPause();
        }
    }

    function handleLikeClick() {
        const songId = parseInt(this.getAttribute('data-song-id'), 10);
        toggleLike(songId, this, data => {
            this.dataset.likes = data.total_likes;
            if (songId === currentSongId) {
                likeButtonPlayer.classList.toggle('liked', data.liked);
                likeButtonPlayer.dataset.likes = data.total_likes;
                if (currentIndex !== -1) playlist[currentIndex].likes = data.total_likes;
            }
        });
    }

    function handlePlayerLikeClick() {
        if (!currentSongId) return;
        toggleLike(currentSongId, likeButtonPlayer, data => {
            document.querySelectorAll(`.like-button[data-song-id="${currentSongId}"]`).forEach(button => {
                button.classList.toggle('liked', data.liked);
                button.dataset.likes = data.total_likes;
            });
            likeButtonPlayer.dataset.likes = data.total_likes;
            if (currentIndex !== -1) playlist[currentIndex].likes = data.total_likes;
        });
    }

    function toggleLike(songId, button, callback) {
        fetch(`/like/${songId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'Content-Type': 'application/json',
            },
        })
            .then(response => response.ok ? response.json() : Promise.reject(response.status))
            .then(data => {
                button.classList.toggle('liked', data.liked);
                button.dataset.likes = data.total_likes;
                callback(data);
            })
            .catch(error => console.error('Ошибка при лайке:', error));
    }

    function resetPlayButtons() {
        document.querySelectorAll('.play-button i').forEach(icon => {
            icon.classList.replace('bi-pause-fill', 'bi-play-fill');
        });
    }

    function updatePlayerLikeState(songId) {
        const songContainer = document.querySelector(`[data-song-id="${songId}"]`);
        const likeButton = songContainer?.querySelector('.like-button');
        const isLiked = likeButton?.classList.contains('liked') || false;
        const likesCount = likeButton ? parseInt(likeButton.dataset.likes) || 0 : 0;
        likeButtonPlayer.classList.toggle('liked', isLiked);
        likeButtonPlayer.dataset.likes = likesCount;
    }

    function savePlayerState() {
        if (!currentSongId || currentIndex === -1) return;
        const song = playlist[currentIndex];
        const songData = {
            id: currentSongId,
            url: audioSource.src,
            title: song.title,
            author: song.author,
            time: audioPlayer.currentTime,
            isPlaying: !audioPlayer.paused,
            volume: audioPlayer.volume,
            likes: parseInt(likeButtonPlayer.dataset.likes) || 0,
            liked: likeButtonPlayer.classList.contains('liked'),
            price: song.price
        };
        localStorage.setItem('currentSong', JSON.stringify(songData));
    }

    function restorePlayerState() {
        const savedSong = JSON.parse(localStorage.getItem('currentSong'));
        if (!savedSong || !savedSong.url) return;

        const songIndex = playlist.findIndex(song => song.id === savedSong.id);
        if (songIndex === -1) return;

        const song = playlist[songIndex];
        audioSource.src = song.url;
        audioPlayer.load();
        audioPlayer.currentTime = savedSong.time || 0;
        audioPlayer.volume = savedSong.volume || 0.5;
        volumeSlider.value = audioPlayer.volume;
        currentSongDisplay.textContent = `${song.title} - ${song.author || 'Неизвестен'}`;
        currentSongId = song.id;
        currentIndex = songIndex;
        likeButtonPlayer.classList.toggle('liked', savedSong.liked || false);
        likeButtonPlayer.dataset.likes = savedSong.likes || 0;
        songPriceElement.textContent = `₽${song.price.toFixed(2)}`;
        songPriceElement.dataset.songId = song.id;
        if (savedSong.isPlaying) {
            audioPlayer.play()
                .then(() => {
                    updatePlayPauseIcon(true);
                    updateAllPlayIcons(currentSongId, true);
                })
                .catch(err => console.error('Ошибка воспроизведения:', err));
        } else {
            updatePlayPauseIcon(false);
            updateAllPlayIcons(currentSongId, false);
        }
        updateMuteIcon();
    }

    function handleSongEnd() {
        resetPlayButtons();
        currentSongId = null;
        currentIndex = -1;
        localStorage.removeItem('currentSong');
        currentSongDisplay.textContent = 'Выберите песню для воспроизведения';
        likeButtonPlayer.classList.remove('liked');
        likeButtonPlayer.dataset.likes = '0';
        songPriceElement.textContent = '₽0.00';
        songPriceElement.dataset.songId = '0';
        updatePlayPauseIcon(false);
    }

    function handleAudioError() {
        console.error('Ошибка аудио, переход к следующей песне');
        playNextSong();
    }

    return { init };
})();