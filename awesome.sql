-- schema.sql

drop database if exists awesome;

create database awesome;

use awesome;

grant select, insert, update, delete on awesome.* to 'web-data'@'localhost' identified by 'web-data';

create table users (
    `id` varchar(50) not null,
    `email` varchar(50) not null,
    `password` varchar(50) not null,
    `admin` bool not null,
    `name` varchar(50) not null,
    `image` varchar(500) not null,
    `created_at` real not null,
    unique key `idx_email` (`email`),
    key `idx_created_at` (`created_at`),
    primary key (`id`)
) engine=innodb default charset=utf8;

create table blogs (
    `id` varchar(50) not null,
    `user_id` varchar(50) not null,
    `user_name` varchar(50) not null,
    `user_image` varchar(500) not null,
    `name` varchar(50) not null,
    `summary` varchar(200) not null,
    `content` mediumtext not null,
    `created_at` real not null,
    key `idx_created_at` (`created_at`),	
    primary key (`id`),
    foreign key (`user_id`) references users(`id`)
) engine=innodb default charset=utf8;

create table comments (
    `id` varchar(50) not null,
    `blog_id` varchar(50) not null,
    `user_id` varchar(50) not null,
    `user_name` varchar(50) not null,
    `user_image` varchar(500) not null,
    `content` mediumtext not null,
    `created_at` real not null,
    key `idx_created_at` (`created_at`),
    primary key (`id`),
    foreign key (`blog_id`) references blogs(`id`),
    foreign key (`user_id`) references users(`id`)
) engine=innodb default charset=utf8;

create table tags (
	`id` varchar(50) not null,
    `content` varchar(50) not null,
    primary key (`id`)
) engine=immodb default charset=utf8;

create table ctx_blog_tag (
	`id` varchar(50) not null,
    `blog_id` varchar(50) not null,
    `tag_id` varchar(50) not null,
    primary key (`id`),
    key `idx_blog_id` (`blog_id`),
    key `idx_tag_id` (`tag_id`),
    foreign key (`blog_id`) references blogs(`id`),
    foreign key (`tag_id`) references tags(`id`)
) engine = InnoDB default charset = utf8;


