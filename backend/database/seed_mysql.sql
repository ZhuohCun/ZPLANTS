INSERT INTO roles (id, role_name) VALUES
(1,'System Administrator'),
(2,'Grounds Maintenance'),
(3,'General User');

INSERT INTO users (id, username, password, real_name, phone, email, role_id, is_disabled, disable_reason, disabled_by_user_id, disabled_time, create_time, update_time) VALUES
(1,'system','a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3','System Administrator','13800000000','system@ynu.edu.cn',1,0,'',NULL,NULL,'2026-03-17 09:00:00','2026-03-17 09:00:00'),
(2,'manager','a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3','Grounds Maintenance','13800000001','manager@ynu.edu.cn',2,0,'',NULL,NULL,'2026-03-17 09:00:00','2026-03-17 09:00:00'),
(3,'student','a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3','General User','13800000002','student@ynu.edu.cn',3,0,'',NULL,NULL,'2026-03-17 09:00:00','2026-03-17 09:00:00' );

INSERT INTO modules (id, module_name, route_path, sort_no) VALUES
(1,'Home','/home',1),
(2,'Plant Recognition','/recognition/upload',2),
(3,'Plant Species','/species',3),
(4,'Plant Management','/plants',4),
(5,'Care Reminders','/care',5),
(6,'Care Method Management','/care/methods-manage',6),
(7,'Feedback Center','/feedback',7),
(8,'User Management','/admin/users',8),
(9,'Operation Logs','/admin/logs',9),
(10,'Zone and Location Management','/admin/locations',10),
(11,'Profile','/profile',11),
(12,'Role Permissions','/admin/access',12),
(13,'Password Hash','/admin/hash',13);

INSERT INTO permissions (id, module_id, permission_name, permission_group, sort_no) VALUES
(1,1,'Open Home',0,1),
(2,2,'Plant Recognition',0,1),(3,2,'View Recognition Records',1,2),
(4,3,'View Plant Species',0,1),(5,3,'View Plant Distribution',1,2),(6,3,'Add Plant Species',2,3),(7,3,'Edit Plant Species',2,4),(8,3,'Delete Plant Species',2,5),
(9,4,'View Plant Management',0,1),(10,4,'Add Plant',2,2),(11,4,'Edit Plant',2,3),(12,4,'Delete Plant',2,4),
(13,5,'View Care Reminders',0,1),(14,5,'Complete Care Reminder',1,2),(15,5,'Dismiss Care Reminder',1,3),
(16,6,'View Care Methods',0,1),(17,6,'Add Care Method',2,2),(18,6,'Edit Care Method',2,3),(19,6,'Delete Care Method',2,4),
(20,7,'View Feedback',0,1),(21,7,'Send Feedback',1,2),(22,7,'Review Feedback',2,3),
(23,8,'View Users',0,1),(24,8,'Edit User',2,2),(25,8,'Disable User',2,3),
(26,9,'View Logs',0,1),
(27,10,'View Zones and Locations',0,1),(28,10,'Add Zone or Location',2,2),(29,10,'Edit Zone or Location',2,3),(30,10,'Delete Zone or Location',2,4),
(31,11,'Open Profile',0,1),(32,11,'Edit Details',1,2),
(33,12,'View Role Permissions',0,1),(34,12,'Configure Role Permissions',2,2),
(35,13,'Generate Password Hash',0,1);

INSERT INTO role_permissions (id, role_id, permission_id, state, update_time) VALUES
(1,1,1,3,'2026-03-17 09:00:00'),(2,1,2,3,'2026-03-17 09:00:00'),(3,1,3,3,'2026-03-17 09:00:00'),(4,1,4,3,'2026-03-17 09:00:00'),(5,1,5,3,'2026-03-17 09:00:00'),(6,1,6,3,'2026-03-17 09:00:00'),(7,1,7,3,'2026-03-17 09:00:00'),(8,1,8,3,'2026-03-17 09:00:00'),(9,1,9,3,'2026-03-17 09:00:00'),(10,1,10,3,'2026-03-17 09:00:00'),(11,1,11,3,'2026-03-17 09:00:00'),(12,1,12,3,'2026-03-17 09:00:00'),(13,1,13,3,'2026-03-17 09:00:00'),(14,1,14,3,'2026-03-17 09:00:00'),(15,1,15,3,'2026-03-17 09:00:00'),(16,1,16,3,'2026-03-17 09:00:00'),(17,1,17,3,'2026-03-17 09:00:00'),(18,1,18,3,'2026-03-17 09:00:00'),(19,1,19,3,'2026-03-17 09:00:00'),(20,1,20,3,'2026-03-17 09:00:00'),(21,1,21,3,'2026-03-17 09:00:00'),(22,1,22,3,'2026-03-17 09:00:00'),(23,1,23,3,'2026-03-17 09:00:00'),(24,1,24,3,'2026-03-17 09:00:00'),(25,1,25,3,'2026-03-17 09:00:00'),(26,1,26,3,'2026-03-17 09:00:00'),(27,1,27,3,'2026-03-17 09:00:00'),(28,1,28,3,'2026-03-17 09:00:00'),(29,1,29,3,'2026-03-17 09:00:00'),(30,1,30,3,'2026-03-17 09:00:00'),(31,1,31,3,'2026-03-17 09:00:00'),(32,1,32,3,'2026-03-17 09:00:00'),(33,1,33,3,'2026-03-17 09:00:00'),(34,1,34,3,'2026-03-17 09:00:00'),(35,1,35,3,'2026-03-17 09:00:00'),
(36,2,1,3,'2026-03-17 09:00:00'),(37,2,2,2,'2026-03-17 09:00:00'),(38,2,3,3,'2026-03-17 09:00:00'),(39,2,4,3,'2026-03-17 09:00:00'),(40,2,5,2,'2026-03-17 09:00:00'),(41,2,6,1,'2026-03-17 09:00:00'),(42,2,7,1,'2026-03-17 09:00:00'),(43,2,8,1,'2026-03-17 09:00:00'),(44,2,9,2,'2026-03-17 09:00:00'),(45,2,10,2,'2026-03-17 09:00:00'),(46,2,11,2,'2026-03-17 09:00:00'),(47,2,12,2,'2026-03-17 09:00:00'),(48,2,13,2,'2026-03-17 09:00:00'),(49,2,14,2,'2026-03-17 09:00:00'),(50,2,15,2,'2026-03-17 09:00:00'),(51,2,16,2,'2026-03-17 09:00:00'),(52,2,17,2,'2026-03-17 09:00:00'),(53,2,18,2,'2026-03-17 09:00:00'),(54,2,19,2,'2026-03-17 09:00:00'),(55,2,20,2,'2026-03-17 09:00:00'),(56,2,21,2,'2026-03-17 09:00:00'),(57,2,22,1,'2026-03-17 09:00:00'),(58,2,23,1,'2026-03-17 09:00:00'),(59,2,24,1,'2026-03-17 09:00:00'),(60,2,25,1,'2026-03-17 09:00:00'),(61,2,26,1,'2026-03-17 09:00:00'),(62,2,27,2,'2026-03-17 09:00:00'),(63,2,28,2,'2026-03-17 09:00:00'),(64,2,29,2,'2026-03-17 09:00:00'),(65,2,30,2,'2026-03-17 09:00:00'),(66,2,31,3,'2026-03-17 09:00:00'),(67,2,32,2,'2026-03-17 09:00:00'),(68,2,33,0,'2026-03-17 09:00:00'),(69,2,34,0,'2026-03-17 09:00:00'),(70,2,35,0,'2026-03-17 09:00:00'),
(71,3,1,3,'2026-03-17 09:00:00'),(72,3,2,2,'2026-03-17 09:00:00'),(73,3,3,3,'2026-03-17 09:00:00'),(74,3,4,3,'2026-03-17 09:00:00'),(75,3,5,2,'2026-03-17 09:00:00'),(76,3,6,1,'2026-03-17 09:00:00'),(77,3,7,1,'2026-03-17 09:00:00'),(78,3,8,1,'2026-03-17 09:00:00'),(79,3,9,1,'2026-03-17 09:00:00'),(80,3,10,1,'2026-03-17 09:00:00'),(81,3,11,1,'2026-03-17 09:00:00'),(82,3,12,1,'2026-03-17 09:00:00'),(83,3,13,1,'2026-03-17 09:00:00'),(84,3,14,1,'2026-03-17 09:00:00'),(85,3,15,1,'2026-03-17 09:00:00'),(86,3,16,1,'2026-03-17 09:00:00'),(87,3,17,1,'2026-03-17 09:00:00'),(88,3,18,1,'2026-03-17 09:00:00'),(89,3,19,1,'2026-03-17 09:00:00'),(90,3,20,2,'2026-03-17 09:00:00'),(91,3,21,2,'2026-03-17 09:00:00'),(92,3,22,1,'2026-03-17 09:00:00'),(93,3,23,1,'2026-03-17 09:00:00'),(94,3,24,1,'2026-03-17 09:00:00'),(95,3,25,1,'2026-03-17 09:00:00'),(96,3,26,1,'2026-03-17 09:00:00'),(97,3,27,1,'2026-03-17 09:00:00'),(98,3,28,1,'2026-03-17 09:00:00'),(99,3,29,1,'2026-03-17 09:00:00'),(100,3,30,1,'2026-03-17 09:00:00'),(101,3,31,3,'2026-03-17 09:00:00'),(102,3,32,2,'2026-03-17 09:00:00'),(103,3,33,0,'2026-03-17 09:00:00'),(104,3,34,0,'2026-03-17 09:00:00'),(105,3,35,0,'2026-03-17 09:00:00');

INSERT INTO campus_zones (id, zone_name, create_time, update_time, is_deleted) VALUES
(1,'Baijia Avenue','2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(2,'Hua Residence','2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(3,'Library','2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(4,'Rose Garden','2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(5,'Central Ginkgo Walk','2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(6,'Cherry Blossom Walk','2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(7,'School of Software','2026-03-17 09:00:00','2026-03-17 09:00:00',0);

INSERT INTO locations (id, zone_id, location_name, create_time, update_time, is_deleted) VALUES
(1,1,'Beside Baijia Avenue','2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(2,2,'Beside Hua Residence','2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(3,3,'Beside the Library','2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(4,4,'Rose Garden','2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(5,5,'Central Ginkgo Walk','2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(6,6,'Cherry Blossom Walk','2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(7,7,'Beside the School of Software','2026-03-17 09:00:00','2026-03-17 09:00:00',0);

INSERT INTO species (id, species_name, scientific_name, care_points, light_requirement, create_time, update_time, is_deleted) VALUES
(1,'Southern Magnolia','Magnolia grandiflora','Keep the soil slightly moist, drain promptly in the rainy season, and trim dead branches in spring and autumn.','Prefers sun and tolerates partial shade','2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(2,'Camellia','Camellia japonica','Keep the air moderately humid, avoid harsh sun, and add phosphorus-potassium fertilizer before flowering.','Prefers partial shade','2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(3,'Rapeseed Flower','Brassica napus','Keep the soil moist during growth and avoid standing water during flowering.','Prefers full sun','2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(4,'Chinese Flowering Crabapple','Malus spectabilis','Fertilize lightly in spring, prune weak branches after flowering, and keep good airflow.','Prefers sun and tolerates light shade','2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(5,'Cherry Blossom','Prunus serrulata','Water moderately around flowering, keep roots airy in summer, and check for pests and disease.','Prefers full sun','2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(6,'Rose','Rosa rugosa','Keep airflow open, remove spent flowers promptly, and fertilize regularly during growth.','Prefers full sun','2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(7,'African Lily','Agapanthus africanus','Let the potting soil dry slightly between watering, and keep water and nutrients balanced during flowering.','Prefers sun, with light summer shade','2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(8,'Gesang Flower','Cosmos bipinnatus','Avoid overwatering, provide enough sunlight, and remove spent flowers.','Prefers full sun','2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(9,'Iris','Iris tectorum','Keep the soil well drained and clear old leaves after flowering.','Prefers sun and tolerates partial shade','2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(10,'Canna Lily','Canna indica','Water generously during growth, remove old leaves after flowering, and add a light follow-up fertilizer.','Prefers full sun','2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(11,'Ginkgo','Ginkgo biloba','Keep the soil loose and water young trees during dry spells.','Prefers full sun','2026-03-17 09:00:00','2026-03-17 09:00:00',0);

INSERT INTO plants (id, species_id, location_id, create_time, update_time, is_deleted) VALUES
(1,1,1,'2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(2,2,2,'2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(3,3,1,'2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(4,4,3,'2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(5,5,6,'2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(6,6,4,'2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(7,7,3,'2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(8,5,7,'2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(9,9,3,'2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(10,10,4,'2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(11,11,5,'2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(12,5,7,'2026-03-17 09:00:00','2026-03-17 09:00:00',0);

INSERT INTO species_images (id, species_id, image_url, create_time, update_time, is_deleted) VALUES
(1,1,'/uploads/plants/default-cover.png','2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(2,2,'/uploads/plants/default-cover.png','2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(3,3,'/uploads/plants/default-cover.png','2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(4,4,'/uploads/plants/default-cover.png','2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(5,5,'/uploads/plants/default-cover.png','2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(6,6,'/uploads/plants/default-cover.png','2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(7,7,'/uploads/plants/default-cover.png','2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(8,8,'/uploads/plants/default-cover.png','2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(9,9,'/uploads/plants/default-cover.png','2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(10,10,'/uploads/plants/default-cover.png','2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(11,11,'/uploads/plants/default-cover.png','2026-03-17 09:00:00','2026-03-17 09:00:00',0);

INSERT INTO care_methods (id, method_name, create_time, update_time, is_deleted) VALUES
(1,'Watering','2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(2,'Fertilizing','2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(3,'Pruning','2026-03-17 09:00:00','2026-03-17 09:00:00',0);

INSERT INTO care_rules (id, species_id, care_method_id, cycle_days, create_time, update_time, is_deleted) VALUES
(1,1,1,5,'2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(2,2,2,14,'2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(3,3,3,21,'2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(4,4,1,3,'2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(5,5,2,10,'2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(6,6,3,15,'2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(7,7,1,4,'2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(8,8,1,6,'2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(9,9,3,18,'2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(10,10,2,12,'2026-03-17 09:00:00','2026-03-17 09:00:00',0),
(11,11,1,7,'2026-03-17 09:00:00','2026-03-17 09:00:00',0);

INSERT INTO care_reminders (id, plant_id, care_rule_id, process_state, is_valid, create_time) VALUES
(1,1,1,2,1,'2026-04-13 09:00:00'),
(2,1,1,1,1,'2026-04-20 09:00:00');

INSERT INTO care_records (id, reminder_id, operator_user_id, operation_status, remark, snapshot_species_name, snapshot_zone_name, snapshot_location_name, snapshot_method_name, snapshot_cycle_days, create_time) VALUES
(1,1,2,1,'Southern Magnolia beside Baijia Avenue was watered','Southern Magnolia','Baijia Avenue','Beside Baijia Avenue','Watering',7,'2026-04-13 09:00:00');

INSERT INTO feedback_types (id, type_name, create_time, update_time) VALUES
(1,'Experience Feedback','2026-03-17 09:00:00','2026-03-17 09:00:00'),
(2,'Recognition Result Feedback','2026-03-17 09:00:00','2026-03-17 09:00:00'),
(3,'Other','2026-03-17 09:00:00','2026-03-17 09:00:00');

INSERT INTO recognitions (id, user_id, species_id, image_url, create_time) VALUES
(1,3,1,'/uploads/plants/default-cover.png','2026-03-17 10:00:00');

INSERT INTO recognition_candidates (id, recognition_id, species_id, confidence, cluster_id) VALUES
(1,1,1,0.91,'cluster-01'),
(2,1,2,0.09,'cluster-01');

INSERT INTO feedbacks (id, user_id, feedback_type_id, recognition_id, content, audit_state, audit_remark, create_time, audit_time, audited_by_user_id) VALUES
(1,3,1,NULL,'The interface feels clean and the recognition response is quick.',1,'','2026-03-17 11:00:00',NULL,NULL),
(2,3,2,1,'The recognition result would be clearer with brief notes on the candidates.',2,'Valid feedback, recorded for improvement.','2026-03-17 11:10:00','2026-03-17 12:00:00',1);

INSERT INTO operation_logs (id, user_id, module_id, operation_name, request_url, request_method, ip, ip_location, create_time) VALUES
(1,1,1,'System Initialization','/api/auth/login','POST','127.0.0.1','Local Address','2026-03-17 09:00:00');


UPDATE role_permissions rp JOIN roles r ON rp.role_id = r.id JOIN permissions p ON rp.permission_id = p.id JOIN modules m ON p.module_id = m.id SET rp.state = 3 WHERE m.route_path = '/recognition/upload' AND p.sort_no = 2;
UPDATE role_permissions rp JOIN roles r ON rp.role_id = r.id JOIN permissions p ON rp.permission_id = p.id JOIN modules m ON p.module_id = m.id SET rp.state = 1 WHERE r.role_name = 'Grounds Maintenance' AND ((m.route_path = '/feedback' AND p.sort_no = 3) OR (m.route_path = '/admin/users') OR (m.route_path = '/admin/logs'));
