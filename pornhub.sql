CREATE DATABASE IF NOT EXISTS `pornhub`;

USE `pornhub`;

DROP TABLE IF EXISTS `video_info`;

CREATE TABLE `video_info` (
	`id` int(20) NOT NULL AUTO_INCREMENT,
	`timestamp` timestamp DEFAULT CURRENT_TIMESTAMP NULL COMMENT '爬取时间',
	`type` varchar(25) DEFAULT NULL COMMENT "视频类型",
	`name` varchar(255) DEFAULT NULL COMMENT "视频名",
	`view_key` varchar(20) DEFAULT NULL COMMENT "视频ID",
	`quality` varchar(10) DEFAULT NULL COMMENT "视频清晰度",
	`size` varchar(20) DEFAULT NULL COMMENT "视频大小：M",
	`duratuib` varchar(20) DEFAULT NULL COMMENT "视频时长",
	`cover` varchar(255) DEFAULT NULL COMMENT "视频封面",
	`mediabook` varchar(255) DEFAULT NULL COMMENT "视频流简介",

	UNIQUE KEY `video_info_view_key` (`view_key`),
	PRIMARY KEY (`id`)
)ENGINE=InnoDB DEFAULT CHARSET=utf8; 
