# Use Ubuntu as base image
FROM ubuntu:22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive

# Update and install dependencies
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
    apache2 \
    mysql-server \
    php \
    libapache2-mod-php \
    php-mysql \
    php-xml \
    php-mbstring \
    php-intl \
    php-curl \
    php-zip \
    php-gd \
    php-ldap \
    php-bcmath \
    wget \
    unzip \
    composer \
    python3 \
    python3-pip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Prevent services from starting automatically
RUN echo exit 0 > /usr/sbin/policy-rc.d

# Configure MySQL
RUN service mysql start && \
    mysql -e "CREATE DATABASE silverstripe_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" && \
    mysql -e "CREATE USER 'silverstripe_user'@'localhost' IDENTIFIED BY 'your_password';" && \
    mysql -e "GRANT ALL PRIVILEGES ON silverstripe_db.* TO 'silverstripe_user'@'localhost';" && \
    mysql -e "FLUSH PRIVILEGES;"

# Install SilverStripe
# Set working directory
WORKDIR /var/www/html/

# Set a timeout for the wget command and verify success
RUN timeout 300 wget https://github.com/silverstripe/silverstripe-installer/archive/refs/tags/4.11.0.tar.gz && \
    echo "Download successful" || (echo "Download failed" && exit 1)

# Extract only if the download succeeded
RUN test -f 4.11.0.tar.gz && tar -xvzf 4.11.0.tar.gz || (echo "Extraction failed" && exit 1)

RUN ls /var/www/html
# Rename the extracted folder to 'silverstripe'
# RUN mv silverstripe-installer-4.11.0 silverstripe

RUN mkdir /var/www/html/silverstripe

RUN cp -r silverstripe-installer-4.11.0/* /var/www/html/silverstripe
# Clean up by removing the tarball
# RUN rm 4.11.0.tar.gz

# Set up permissions
RUN chown -R www-data:www-data /var/www/html/silverstripe && \
    find /var/www/html/silverstripe -type d -exec chmod 755 {} \; && \
    find /var/www/html/silverstripe -type f -exec chmod 644 {} \;

# Configure Apache
COPY silverstripe.conf /etc/apache2/sites-available/
RUN a2ensite silverstripe.conf && \
    a2enmod rewrite

COPY silverstripe.conf /etc/apache2/sites-available/

WORKDIR /var/www/html/silverstripe
# RUN composer install
RUN composer install --no-interaction --optimize-autoloader && echo "Composer installation complete."

# Add ServerName to Apache config
RUN echo "ServerName localhost" >> /etc/apache2/apache2.conf

# Modify Apache default site configuration
RUN sed -i 's|DocumentRoot /var/www/html|DocumentRoot /var/www/html/silverstripe/public|g' /etc/apache2/sites-available/000-default.conf

RUN sed -i '/DocumentRoot \/var\/www\/html/a\        <Directory /var/www/html/silverstripe/public>\n            AllowOverride All\n            Require all granted\n        </Directory>' /etc/apache2/sites-available/000-default.conf

# Start Apache in the foreground
CMD ["apachectl", "-D", "FOREGROUND"]

# Create .env file and add environment variables
RUN echo "SS_DATABASE_CLASS=\"MySQLDatabase\"" > /var/www/html/silverstripe/.env && \
    echo "SS_DATABASE_NAME=\"silverstripe_db\"" >> /var/www/html/silverstripe/.env && \
    echo "SS_DATABASE_SERVER=\"mysql\"" >> /var/www/html/silverstripe/.env && \
    echo "SS_DATABASE_USERNAME=\"silverstripe_user\"" >> /var/www/html/silverstripe/.env && \
    echo "SS_DATABASE_PASSWORD=\"your_password\"" >> /var/www/html/silverstripe/.env

# Set file permissions
RUN chown -R www-data:www-data /var/www/html/silverstripe && \
    find /var/www/html/silverstripe -type d -exec chmod 755 {} \; && \
    find /var/www/html/silverstripe -type f -exec chmod 644 {} \;

RUN chmod +x /var/www/html/silverstripe/vendor/bin/sake && \
    chmod +x /var/www/html/silverstripe/vendor/silverstripe/framework/sake

# Copy the entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Set the entrypoint
ENTRYPOINT ["docker-entrypoint.sh"]

# Open ports
EXPOSE 80

# Start Apache and MySQL
CMD apachectl -D FOREGROUND