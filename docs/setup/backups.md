# Backups

It is recommended to make periodic backups and ideally also before major version upgrades.

## Backup

### Database Backup
To create a backup of your database you can run the following command

???+ Info 
    Either the whole compose or at least the `db` container must be up and running to be able to use `exec`.

=== "Docker"
    ```sh
    docker compose -f docker-compose.prod.yml exec db pg_dump -U django -d django > wine-cellar-postgres-backup-$(date +%F).sql
    ```

=== "Podman"
    ```sh
    podman-compose -f docker-compose.prod.yml exec db pg_dump -U django -d django > wine-cellar-postgres-backup-$(date +%F).sql
    ```



### Media Backup
To backup the user uploaded media the easiest way is to just make a backup or copy of the volume. In a default configuration the
path should be

=== "Docker"
    ```sh
    /var/lib/docker/volumes/wine-cellar_media_volume/_data
    ```

=== "Podman"
    ```sh
    /var/lib/containers/storage/volumes/wine-cellar_media_volume/_data/
    ```

If that path doesn't exist you can use the `inspect` command to find the correct one:

=== "Docker"
    ```sh
    docker volume inspect wine-cellar_media_volume      
    ```

=== "Podman"
    ```sh
    podman volume inspect wine-cellar_media_volume      
    ```

## Restore

Before attempting to restore make sure your database backup is valid. To do so open the `sql` file and check that it starts with something similar to:

```sql
--
-- PostgreSQL database dump
--

-- Dumped from database version 16.11 (Debian 16.11-1.pgdg13+1)
-- Dumped by pg_dump version 16.11 (Debian 16.11-1.pgdg13+1)
```

### Restore Database

#### Stop Containers
We only want the db container to run for this step.

=== "Docker"
    ```sh
    docker compose -f docker-compose.prod.yml down
    docker compose -f docker-compose.prod.yml up -d db
    ```

=== "Podman"
    ```sh
    podman-compose -f docker-compose.prod.yml down 
    podman-compose -f docker-compose.prod.yml up -d db
    ```

#### Recreate empty database

=== "Docker"
    ```sh
    docker compose -f docker-compose.prod.yml exec db psql -U django -d postgres -c "DROP DATABASE django;"
    docker compose -f docker-compose.prod.yml exec db psql -U django -d postgres -c "CREATE DATABASE django;"
    ```

=== "Podman"
    ```sh
    podman-compose -f docker-compose.prod.yml exec db psql -U django -d postgres -c "DROP DATABASE django;"
    podman-compose -f docker-compose.prod.yml exec db psql -U django -d postgres -c "CREATE DATABASE django;"
    ```

#### Restore database

=== "Docker"
    ```sh
    docker compose -f docker-compose.prod.yml exec -T db psql -U django -d django < wine-cellar-postgres-backup-<date>.sql
    ```

=== "Podman"
    ```sh
    podman-compose -f docker-compose.prod.yml exec -T db psql -U django -d django < wine-cellar-postgres-backup-<date>.sql
    ```

### Restore Media Folder
Copy the backup of the media folder to the media volume. Make sure the folder has the correct permissions.

### Restart

=== "Docker"
    ```sh
    docker compose -f docker-compose.prod.yml down
    docker compose -f docker-compose.prod.yml up -d
    ```

=== "Podman"
    ```sh
    podman-compose -f docker-compose.prod.yml down 
    podman-compose -f docker-compose.prod.yml up -d
    ```