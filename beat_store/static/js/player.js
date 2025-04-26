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

    // Получаем CSRF-токен из мета-тега
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';
    if (!csrfToken) {
        console.error('CSRF-токен не найден. Убедитесь, что мета-тег <meta name="csrf-token"> присутствует в HTML.');
    }

    // Инициализация плеера
    function init(songsData = []) {
        updatePlaylist(songsData);

        // Проверяем наличие всех необходимых элементов DOM
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

        // Устанавливаем начальную громкость из localStorage или по умолчанию
        audioPlayer.volume = parseFloat(localStorage.getItem('volume')) || 0.5;
        volumeSlider.value = audioPlayer.volume;
        setupEventListeners();
        restorePlayerState();
    }

    // Обновление плейлиста
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

        // Обновляем плейлист только если он изменился
        if (JSON.stringify(playlist) !== JSON.stringify(newSongs)) {
            playlist = newSongs;
            currentIndex = playlist.findIndex(song => song.id === currentSongId);
        }
    }

    // Установка обработчиков событий
    function setupEventListeners() {
        // Обработчики для кнопок воспроизведения
        document.querySelectorAll('.play-button').forEach(button => {
            button.removeEventListener('click', handlePlayClick);
            button.addEventListener('click', handlePlayClick);
            button.addEventListener('touchend', handlePlayClick);
        });

        // Обработчики для кнопок лайков
        document.querySelectorAll('.like-button').forEach(button => {
            button.removeEventListener('click', handleLikeClick);
            button.addEventListener('click', handleLikeClick);
            button.addEventListener('touchend', handleLikeClick);
        });

        // События плеера
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

        // Обработчики для элементов управления плеером
        likeButtonPlayer.addEventListener('click', handlePlayerLikeClick);
        likeButtonPlayer.addEventListener('touchend', handlePlayerLikeClick);
        playPauseButton.addEventListener('click', togglePlayPause);
        playPauseButton.addEventListener('touchend', togglePlayPause);
        prevButton.addEventListener('click', playPreviousSong);
        prevButton.addEventListener('touchend', playPreviousSong);
        nextButton.addEventListener('click', playNextSong);
        nextButton.addEventListener('touchend', playNextSong);
        volumeSlider.addEventListener('input', () => {
            audioPlayer.volume = parseFloat(volumeSlider.value);
            updateMuteIcon();
            localStorage.setItem('volume', audioPlayer.volume);
        });
        muteButton.addEventListener('click', toggleMute);
        muteButton.addEventListener('touchend', toggleMute);
        progressBar.addEventListener('input', () => {
            audioPlayer.currentTime = progressBar.value * audioPlayer.duration;
            savePlayerState();
        });

        // Обработчик для кнопки добавления в корзину
        songPriceElement.addEventListener('click', handleAddToCart);
        songPriceElement.addEventListener('touchend', handleAddToCart);

        window.addEventListener('load', restorePlayerState);
        document.addEventListener('keydown', handleKeyboardControls);
    }

    // Обработчик клика по кнопке воспроизведения
    function handlePlayClick(e) {
        e.preventDefault();
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

    // Обработчик добавления в корзину
    function handleAddToCart(e) {
        e.preventDefault();
        const songId = parseInt(songPriceElement.dataset.songId, 10);
        if (!songId) {
            console.error('ID песни для корзины не указан');
            return;
        }
        addToCart(songId);
    }

    // Асинхронная функция добавления песни в корзину
    async function addToCart(songId) {
        try {
            console.log(`Отправка запроса на добавление песни ${songId} в корзину: /cart/add/${songId}/`);
            const response = await fetch(`/cart/add/${songId}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(`HTTP ошибка: ${response.status} ${data.message || 'Нет сообщения'}`);
            }

            if (data.success) {
                console.log(`Песня ${songId} успешно добавлена в корзину:`, data.message);
                document.querySelectorAll(`.cart-button[data-song-id="${songId}"]`).forEach(button => {
                    button.disabled = true;
                });
                songPriceElement.disabled = true;
                alert(data.message);
            } else {
                console.warn(`Не удалось добавить песню ${songId} в корзину:`, data.message);
                alert(data.message);
            }
        } catch (error) {
            console.error(`Ошибка при добавлении песни ${songId} в корзину:`, error.message);
            let userMessage = 'Произошла ошибка при добавлении в корзину.';
            if (error.message.includes('403')) {
                userMessage = 'Пожалуйста, войдите в аккаунт.';
            } else if (error.message.includes('404')) {
                userMessage = 'Песня не найдена.';
            }
            alert(userMessage);
        }
    }

    // Воспроизведение песни
    function playSong(songIndex) {
        const song = playlist[songIndex];
        if (!song) return;

        resetPlayButtons();
        audioSource.src = song.url;
        audioPlayer.load();

        const playPromise = audioPlayer.play();
        if (playPromise !== undefined) {
            playPromise
                .then(() => {
                    currentSongId = song.id;
                    currentIndex = songIndex;
                    currentSongDisplay.textContent = `${song.title} - ${song.author || 'Неизвестен'}`;
                    songPriceElement.textContent = `₽${song.price.toFixed(2)}`;
                    songPriceElement.dataset.songId = song.id;
                    fetchCartState(song.id).then(inCart => {
                        songPriceElement.disabled = inCart;
                    });
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
    }

    // Получение состояния корзины с сервера
    async function fetchCartState(songId) {
        try {
            const response = await fetch('/cart/', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
            });
            const data = await response.json();
            return data.songs.some(song => song.id === songId);
        } catch (error) {
            console.error('Ошибка при получении состояния корзины:', error);
            return false;
        }
    }

    // Обновление прогресс-бара
    function updateProgress() {
        if (!audioPlayer.duration) return;
        progressBar.value = audioPlayer.currentTime / audioPlayer.duration;
        currentTimeDisplay.textContent = formatTime(audioPlayer.currentTime);
        totalTimeDisplay.textContent = formatTime(audioPlayer.duration);
    }

    // Обновление отображения времени
    function updateTimeDisplay() {
        totalTimeDisplay.textContent = formatTime(audioPlayer.duration);
        currentTimeDisplay.textContent = formatTime(audioPlayer.currentTime);
    }

    // Увеличение счетчика воспроизведений
    async function incrementPlayCount(songId) {
        try {
            console.log(`Отправка запроса на увеличение счетчика воспроизведений для песни ${songId}: /play-song/${songId}/`);
            const response = await fetch(`/play-song/${songId}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
            });

            if (!response.ok) {
                throw new Error(`HTTP ошибка: ${response.status}`);
            }

            const data = await response.json();
            console.log(`Счетчик воспроизведений для песни ${songId} обновлен:`, data.total_plays);
            const playCountElement = document.getElementById(`plays-count-${songId}`);
            if (playCountElement) {
                playCountElement.innerHTML = `<i class="bi bi-play-fill"></i> ${data.total_plays}`;
            }
            if (currentIndex !== -1) {
                playlist[currentIndex].plays = data.total_plays;
            }
        } catch (error) {
            console.error(`Ошибка при увеличении счетчика для песни ${songId}:`, error);
        }
    }

    // Воспроизведение следующей песни
    function playNextSong() {
        if (currentIndex < playlist.length - 1 && currentIndex !== -1) {
            playSong(currentIndex + 1);
        } else {
            handleSongEnd();
        }
    }

    // Воспроизведение предыдущей песни
    function playPreviousSong() {
        if (currentIndex > 0 && currentIndex !== -1) {
            playSong(currentIndex - 1);
        }
    }

    // Переключение воспроизведения/паузы
    function togglePlayPause() {
        if (!currentSongId) return;

        if (audioPlayer.paused) {
            const playPromise = audioPlayer.play();
            if (playPromise !== undefined) {
                playPromise
                    .then(() => {
                        updatePlayPauseIcon(true);
                        updateAllPlayIcons(currentSongId, true);
                    })
                    .catch(err => console.error('Ошибка воспроизведения:', err));
            }
        } else {
            audioPlayer.pause();
            updatePlayPauseIcon(false);
            updateAllPlayIcons(currentSongId, false);
        }
        savePlayerState();
    }

    // Переключение режима без звука
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

    // Обновление иконки звука
    function updateMuteIcon() {
        const icon = muteButton.querySelector('i');
        icon.classList.toggle('bi-volume-mute-fill', audioPlayer.volume === 0);
        icon.classList.toggle('bi-volume-up-fill', audioPlayer.volume > 0);
    }

    // Обновление иконки воспроизведения/паузы
    function updatePlayPauseIcon(isPlaying) {
        const icon = playPauseButton.querySelector('i');
        icon.classList.toggle('bi-play-fill', !isPlaying);
        icon.classList.toggle('bi-pause-fill', isPlaying);
    }

    // Обновление иконок воспроизведения для всех кнопок
    function updateAllPlayIcons(songId, isPlaying) {
        document.querySelectorAll(`.play-button[data-song-id="${songId}"] i`).forEach(icon => {
            icon.classList.toggle('bi-play-fill', !isPlaying);
            icon.classList.toggle('bi-pause-fill', isPlaying);
        });
    }

    // Форматирование времени
    function formatTime(seconds) {
        if (isNaN(seconds)) return '0:00';
        const minutes = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${minutes}:${secs < 10 ? '0' : ''}${secs}`;
    }

    // Обработка клавиатурных команд
    function handleKeyboardControls(e) {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
        if (e.key === 'ArrowRight') playNextSong();
        if (e.key === 'ArrowLeft') playPreviousSong();
        if (e.key === ' ') {
            e.preventDefault();
            togglePlayPause();
        }
    }

    // Обработчик клика по кнопке лайка
    function handleLikeClick(e) {
        e.preventDefault();
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

    // Обработчик клика по кнопке лайка в плеере
    function handlePlayerLikeClick(e) {
        e.preventDefault();
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

    // Переключение лайка
    async function toggleLike(songId, button, callback) {
        try {
            console.log(`Отправка запроса на лайк/удаление лайка для песни ${songId}: /like/${songId}/`);
            console.log('CSRF-токен:', csrfToken);
            const response = await fetch(`/like/${songId}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify({})
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(`HTTP ошибка: ${response.status} ${data.message || 'Нет сообщения'}`);
            }

            if (data.success) {
                console.log(`Лайк для песни ${songId} успешно обработан:`, data);
                button.classList.toggle('liked', data.liked);
                button.dataset.likes = data.total_likes;
                // Синхронизируем все кнопки лайков для этой песни
                document.querySelectorAll(`.like-button[data-song-id="${songId}"]`).forEach(btn => {
                    btn.classList.toggle('liked', data.liked);
                    btn.dataset.likes = data.total_likes;
                });
                callback(data);
            } else {
                console.warn(`Не удалось обработать лайк для песни ${songId}:`, data.message);
                alert(data.message || 'Не удалось поставить/убрать лайк.');
            }
        } catch (error) {
            console.error(`Ошибка при обработке лайка для песни ${songId}:`, error.message);
            let userMessage = 'Не удалось поставить/убрать лайк. Проверьте, авторизованы ли вы.';
            if (error.message.includes('403')) {
                userMessage = 'Пожалуйста, войдите в аккаунт.';
            } else if (error.message.includes('404')) {
                userMessage = 'Песня не найдена.';
            }
            alert(userMessage);
        }
    }

    // Сброс иконок воспроизведения
    function resetPlayButtons() {
        document.querySelectorAll('.play-button i').forEach(icon => {
            icon.classList.replace('bi-pause-fill', 'bi-play-fill');
        });
    }

    // Обновление состояния кнопки лайка в плеере
    function updatePlayerLikeState(songId) {
        const songContainer = document.querySelector(`[data-song-id="${songId}"]`);
        const likeButton = songContainer?.querySelector('.like-button');
        const isLiked = likeButton?.classList.contains('liked') || false;
        const likesCount = likeButton ? parseInt(likeButton.dataset.likes) || 0 : 0;
        likeButtonPlayer.classList.toggle('liked', isLiked);
        likeButtonPlayer.dataset.likes = likesCount;
    }

    // Сохранение состояния плеера
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
            price: song.price,
        };
        localStorage.setItem('currentSong', JSON.stringify(songData));
    }

    // Восстановление состояния плеера
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

        fetchCartState(song.id).then(inCart => {
            songPriceElement.disabled = inCart;
        });

        if (savedSong.isPlaying) {
            const playPromise = audioPlayer.play();
            if (playPromise !== undefined) {
                playPromise
                    .then(() => {
                        updatePlayPauseIcon(true);
                        updateAllPlayIcons(currentSongId, true);
                    })
                    .catch(err => console.error('Ошибка воспроизведения:', err));
            }
        } else {
            updatePlayPauseIcon(false);
            updateAllPlayIcons(currentSongId, false);
        }
        updateMuteIcon();
    }

    // Обработка завершения песни
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
        songPriceElement.disabled = true;
        updatePlayPauseIcon(false);
    }

    // Обработка ошибок аудио
    function handleAudioError() {
        console.error('Ошибка аудио, переход к следующей песне');
        playNextSong();
    }

    return { init, addToCart };
})();