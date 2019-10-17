-- Create statement for a mysql backend


CREATE TABLE `biorxiv` (
 `source` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'biorxiv',
 `id` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL,
 `created` datetime NOT NULL,
 `title` text COLLATE utf8mb4_unicode_ci NOT NULL,
 `parse_status` smallint(1) NOT NULL DEFAULT '0',
 `parse_data` mediumtext COLLATE utf8mb4_unicode_ci,
 `pages` mediumtext COLLATE utf8mb4_unicode_ci NOT NULL,
 `page_count` smallint(5) unsigned NOT NULL DEFAULT '0',
 `posted_date` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL,
 `author_contact` text COLLATE utf8mb4_unicode_ci,
 `email_sent` tinyint(4) DEFAULT NULL,
 PRIMARY KEY (`id`),
 UNIQUE KEY `id` (`id`),
 KEY `parse_status` (`parse_status`),
 KEY `page_count` (`page_count`)
)

