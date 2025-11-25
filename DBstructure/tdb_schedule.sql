-- MySQL dump 10.13  Distrib 8.0.36, for Win64 (x86_64)
--
-- Host: tdb.cxc48q26c73q.ap-southeast-2.rds.amazonaws.com    Database: tdb
-- ------------------------------------------------------
-- Server version	8.0.42

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;
SET @MYSQLDUMP_TEMP_LOG_BIN = @@SESSION.SQL_LOG_BIN;
SET @@SESSION.SQL_LOG_BIN= 0;

--
-- GTID state at the beginning of the backup 
--

SET @@GLOBAL.GTID_PURGED=/*!80000 '+'*/ '';

--
-- Table structure for table `schedule`
--

DROP TABLE IF EXISTS `schedule`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `schedule` (
  `schedule_id` varchar(50) NOT NULL,
  `group_id` varchar(50) DEFAULT NULL,
  `user_id` varchar(50) DEFAULT NULL,
  `medi_id` varchar(50) DEFAULT NULL,
  `day_of_week` enum('mon','tue','wed','thu','fri','sat','sun') NOT NULL,
  `time_of_day` enum('morning','afternoon','evening') NOT NULL,
  `dose` int NOT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`schedule_id`),
  UNIQUE KEY `user_id` (`user_id`,`medi_id`,`day_of_week`,`time_of_day`),
  KEY `group_id` (`group_id`),
  KEY `medi_id` (`medi_id`,`group_id`),
  CONSTRAINT `schedule_ibfk_1` FOREIGN KEY (`group_id`) REFERENCES `user_group` (`group_id`),
  CONSTRAINT `schedule_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`),
  CONSTRAINT `schedule_ibfk_3` FOREIGN KEY (`medi_id`, `group_id`) REFERENCES `medicine` (`medi_id`, `group_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `schedule`
--

LOCK TABLES `schedule` WRITE;
/*!40000 ALTER TABLE `schedule` DISABLE KEYS */;
INSERT INTO `schedule` VALUES ('0093042b-de82-4436-83f0-fc3d84d9f148','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','medicine_1762787136492','mon','morning',1,'2025-11-11 00:15:55'),('073ef7c6-543f-4702-8868-69f1351c2395','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','medicine_1762787136492','fri','morning',1,'2025-11-11 00:15:55'),('1543e6b0-32c5-46e4-b3b8-08ac70a07d7e','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','supplement_1762787919297','sun','morning',1,'2025-11-11 00:19:10'),('169ff249-b761-42ff-88c2-851a8d7b1506','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','medicine_1762787136492','fri','afternoon',1,'2025-11-11 00:15:55'),('194d99e5-c386-43f7-a932-649a9256a89d','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','medicine_1762787136492','tue','evening',1,'2025-11-11 00:15:55'),('1eee3e60-d48b-4990-96f5-47fc3ca93df8','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','medicine_1762787136492','tue','morning',1,'2025-11-11 00:15:55'),('36779937-0bb1-4b98-9891-4c9ad6e3d08e','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','supplement_1762787919297','fri','morning',1,'2025-11-11 00:19:10'),('3e534412-4cae-4bb9-882c-85068600f97c','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','supplement_1762787919297','thu','evening',1,'2025-11-11 00:19:10'),('442a9753-cce5-4bdd-af1d-dabeb53f680b','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','medicine_1762787587816','sun','evening',1,'2025-11-11 00:19:54'),('4e92368b-7b6a-488a-a889-e49e39d5d355','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','medicine_1762787587816','mon','afternoon',1,'2025-11-11 00:19:54'),('555bf6f0-a86b-43d6-8262-d3660a806d2d','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','medicine_1762787587816','fri','evening',1,'2025-11-11 00:19:54'),('557cddcd-1c3f-4c78-aa74-90358473bf2d','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','medicine_1762787136492','tue','afternoon',1,'2025-11-11 00:15:55'),('5614cc2c-efba-4ed2-98f8-c6ae5e689a14','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','supplement_1762787919297','tue','evening',1,'2025-11-11 00:19:10'),('5abb14aa-fa8f-4eab-b389-cdcc8cc4a862','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','medicine_1762787136492','sat','evening',1,'2025-11-11 00:15:55'),('5e9464b9-9fb6-4b2b-9c51-14b976ee578c','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','medicine_1762787587816','thu','evening',1,'2025-11-11 00:19:54'),('6026fb88-be04-4ef0-852b-7b9f781619c8','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','supplement_1762787919297','sat','morning',1,'2025-11-11 00:19:10'),('638ab3f6-3bd7-479b-bcde-147effef4c82','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','medicine_1762787587816','tue','evening',1,'2025-11-11 00:19:54'),('66c5a971-c921-4efe-8587-8bfc2d536234','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','supplement_1762787919297','wed','morning',1,'2025-11-11 00:19:10'),('77960a63-1d32-4dd3-bbd9-b79bef0986fb','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','medicine_1762787587816','wed','afternoon',1,'2025-11-11 00:19:54'),('7a3d1cb5-e1e9-4a80-a02b-aecde1f4edd5','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','medicine_1762787587816','wed','evening',1,'2025-11-11 00:19:54'),('7e42b42f-0b90-4d63-b235-52dc41edd77f','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','supplement_1762787919297','sun','evening',1,'2025-11-11 00:19:10'),('7f2bbb6f-3d3b-475d-a41f-2ba6188825d5','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','medicine_1762787587816','thu','afternoon',1,'2025-11-11 00:19:54'),('83f1f30e-7430-497f-8bcd-d2c126cb5801','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','medicine_1762787136492','sat','morning',1,'2025-11-11 00:15:55'),('8ae928fd-5ed4-40cc-99fc-4d16302b9e13','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','medicine_1762787587816','sat','afternoon',1,'2025-11-11 00:19:54'),('8ee66750-62cb-448f-b83d-0494d689176f','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','medicine_1762787136492','mon','evening',1,'2025-11-11 00:15:55'),('93774e42-688d-44a4-8b12-68def5c58297','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','supplement_1762787919297','mon','evening',1,'2025-11-11 00:19:10'),('946c5c5b-03dc-4bab-8726-9b878ded7123','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','supplement_1762787919297','wed','evening',1,'2025-11-11 00:19:10'),('94961ce4-e760-401f-ada3-e3f98df7e89b','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','medicine_1762787587816','fri','afternoon',1,'2025-11-11 00:19:54'),('9b18d517-9c2e-4b00-bbb7-3c4550ca7e08','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','medicine_1762787136492','wed','evening',1,'2025-11-11 00:15:55'),('9d706e63-a840-45ae-ac54-ed36da81204b','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','medicine_1762787136492','sat','afternoon',1,'2025-11-11 00:15:55'),('a019cce8-9610-485b-90ab-231131b7c9de','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','medicine_1762787136492','wed','afternoon',1,'2025-11-11 00:15:55'),('a45be5d4-ffae-414c-a232-368b9fea91b5','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','medicine_1762787136492','wed','morning',1,'2025-11-11 00:15:55'),('ad56190a-7899-4a44-861d-cb26bf62aee3','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','medicine_1762787587816','sun','afternoon',1,'2025-11-11 00:19:54'),('b7f27fca-e878-4bd1-a65f-5ec9e310d741','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','medicine_1762787136492','thu','evening',1,'2025-11-11 00:15:55'),('c113c751-7dcf-4575-b0a2-f9be38083cfc','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','medicine_1762787587816','tue','afternoon',1,'2025-11-11 00:19:54'),('ca59f0ae-b202-44fb-948e-0f7d7ee21ff2','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','medicine_1762787136492','sun','afternoon',1,'2025-11-11 00:15:55'),('cb177497-3e5f-42ba-b8fb-90bd2c757e7a','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','supplement_1762787919297','sat','evening',1,'2025-11-11 00:19:10'),('cf2b2385-162f-47a2-bd02-0021e46a1a3a','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','supplement_1762787919297','thu','morning',1,'2025-11-11 00:19:10'),('d1dd7d17-728b-4eaf-b0e2-07f53ea2232b','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','medicine_1762787136492','mon','afternoon',1,'2025-11-11 00:15:55'),('d6fae6a8-1289-4fad-8f5d-206fbef5212d','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','medicine_1762787587816','mon','evening',1,'2025-11-11 00:19:54'),('d9b222db-5728-4bf8-8c08-70e410bad226','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','medicine_1762787136492','fri','evening',1,'2025-11-11 00:15:55'),('d9f44d93-a584-4419-9932-795d371068bd','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','medicine_1762787136492','thu','morning',1,'2025-11-11 00:15:55'),('ddadbf4b-a90f-4396-b14c-0beaa0eab9ad','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','medicine_1762787587816','sat','evening',1,'2025-11-11 00:19:54'),('e7ab14b4-c284-42b6-8afc-239b6700d1b3','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','supplement_1762787919297','fri','evening',1,'2025-11-11 00:19:10'),('e8a3b887-dda6-417c-97b0-6eb0f3924d43','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','medicine_1762787136492','sun','evening',1,'2025-11-11 00:15:55'),('e9025af9-11d3-4671-8eaa-ae4ed74d3a6e','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','supplement_1762787919297','mon','morning',1,'2025-11-11 00:19:10'),('e92202c1-81dc-4a4c-8d0e-161f8d7ebd09','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','medicine_1762787136492','sun','morning',1,'2025-11-11 00:15:55'),('f3e74092-6783-48ca-a62c-40673390d52b','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','supplement_1762787919297','tue','morning',1,'2025-11-11 00:19:10'),('fdb80367-fb15-4711-b95a-861b5aa75b9c','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','medicine_1762787136492','thu','afternoon',1,'2025-11-11 00:15:55');
/*!40000 ALTER TABLE `schedule` ENABLE KEYS */;
UNLOCK TABLES;
SET @@SESSION.SQL_LOG_BIN = @MYSQLDUMP_TEMP_LOG_BIN;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-11-12  0:54:53
