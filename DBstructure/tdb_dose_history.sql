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
-- Table structure for table `dose_history`
--

DROP TABLE IF EXISTS `dose_history`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dose_history` (
  `history_id` varchar(50) NOT NULL,
  `group_id` varchar(50) DEFAULT NULL,
  `user_id` varchar(50) DEFAULT NULL,
  `medi_id` varchar(50) DEFAULT NULL,
  `time_of_day` enum('morning','afternoon','evening') NOT NULL,
  `dose_date` date NOT NULL,
  `scheduled_dose` int NOT NULL,
  `actual_dose` int NOT NULL DEFAULT '0',
  `status` enum('completed','missed','partial') NOT NULL DEFAULT 'missed',
  `completed_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `notes` text,
  PRIMARY KEY (`history_id`),
  KEY `group_id` (`group_id`),
  KEY `user_id` (`user_id`),
  KEY `medi_id` (`medi_id`,`group_id`),
  CONSTRAINT `dose_history_ibfk_1` FOREIGN KEY (`group_id`) REFERENCES `user_group` (`group_id`),
  CONSTRAINT `dose_history_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`),
  CONSTRAINT `dose_history_ibfk_3` FOREIGN KEY (`medi_id`, `group_id`) REFERENCES `medicine` (`medi_id`, `group_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dose_history`
--

LOCK TABLES `dose_history` WRITE;
/*!40000 ALTER TABLE `dose_history` DISABLE KEYS */;
INSERT INTO `dose_history` VALUES ('',NULL,NULL,NULL,'','0000-00-00',0,0,'','0000-00-00 00:00:00.000000',NULL),('09e16b20-51dd-4a97-999b-930c4d20a8e6','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','medicine_1762787136492','morning','2025-11-11',2,2,'completed','2025-11-11 23:26:48.943000','Machine: F7F8F9AA, ClientTx: N/A'),('39b3cc19-98d9-43d0-8dcd-77d7f14af2e3','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','medicine_1762787136492','afternoon','2025-11-11',2,2,'completed','2025-11-11 22:05:46.498000','Machine: F7F8F9AA, ClientTx: N/A'),('47393a60-ceae-4cd9-a270-2e632984e4d3','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','medicine_1762787136492','evening','2025-11-11',3,3,'completed','2025-11-11 22:05:56.585000','Machine: F7F8F9AA, ClientTx: N/A'),('4d4b2e7c-15e0-4ecb-86cf-d5e402875dec','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','medicine_1762787136492','evening','2025-11-11',3,3,'completed','2025-11-11 23:27:06.508000','Machine: F7F8F9AA, ClientTx: N/A'),('634ddde6-8c32-4c3a-8509-388b178dc54b','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','medicine_1762787136492','morning','2025-11-11',2,2,'completed','2025-11-11 22:05:38.961000','Machine: F7F8F9AA, ClientTx: N/A'),('d4f9719e-61c8-4873-b9a9-c48858f30a56','d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2','test12','medicine_1762787136492','afternoon','2025-11-11',2,2,'completed','2025-11-11 23:26:56.437000','Machine: F7F8F9AA, ClientTx: N/A');
/*!40000 ALTER TABLE `dose_history` ENABLE KEYS */;
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

-- Dump completed on 2025-11-12  0:54:35
