FROM php:7.4-cli

WORKDIR /app

RUN apt-get update && apt-get install -y \
    librabbitmq-dev \
    libssh-dev \
    git \
    unzip \
    && pecl install amqp \
    && docker-php-ext-enable amqp \
    && docker-php-ext-install sockets

COPY --from=composer:latest /usr/bin/composer /usr/bin/composer

COPY composer.json .

RUN composer install

COPY verifier.php .
COPY .env .

CMD ["php", "verifier.php"]
