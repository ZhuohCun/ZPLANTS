SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS care_records;
DROP TABLE IF EXISTS care_reminders;
DROP TABLE IF EXISTS care_rules;
DROP TABLE IF EXISTS species_images;
DROP TABLE IF EXISTS plants;
DROP TABLE IF EXISTS recognition_candidates;
DROP TABLE IF EXISTS feedbacks;
DROP TABLE IF EXISTS recognitions;
DROP TABLE IF EXISTS feedback_types;
DROP TABLE IF EXISTS care_methods;
DROP TABLE IF EXISTS species;
DROP TABLE IF EXISTS locations;
DROP TABLE IF EXISTS campus_zones;
DROP TABLE IF EXISTS role_permissions;
DROP TABLE IF EXISTS permissions;
DROP TABLE IF EXISTS modules;
DROP TABLE IF EXISTS operation_logs;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS roles;

CREATE TABLE roles (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  role_name VARCHAR(128) UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE users (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) UNIQUE,
  password VARCHAR(255),
  real_name VARCHAR(128) DEFAULT '',
  phone VARCHAR(32) DEFAULT '',
  email VARCHAR(128) DEFAULT '',
  role_id BIGINT,
  is_disabled TINYINT NOT NULL DEFAULT 0,
  disable_reason VARCHAR(255) DEFAULT '',
  disabled_by_user_id BIGINT,
  disabled_time DATETIME,
  create_time DATETIME,
  update_time DATETIME,
  KEY idx_users_role_id (role_id),
  KEY idx_users_disabled_by_user_id (disabled_by_user_id),
  CONSTRAINT fk_users_role_id FOREIGN KEY (role_id) REFERENCES roles(id) ON UPDATE CASCADE ON DELETE SET NULL,
  CONSTRAINT fk_users_disabled_by_user_id FOREIGN KEY (disabled_by_user_id) REFERENCES users(id) ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE modules (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  module_name VARCHAR(128),
  route_path VARCHAR(255) DEFAULT '',
  sort_no INT DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE permissions (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  module_id BIGINT,
  permission_name VARCHAR(128),
  permission_group TINYINT DEFAULT 0,
  sort_no INT DEFAULT 1,
  UNIQUE KEY uk_permissions_module_sort (module_id, sort_no),
  KEY idx_permissions_module_id (module_id),
  CONSTRAINT fk_permissions_module_id FOREIGN KEY (module_id) REFERENCES modules(id) ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE role_permissions (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  role_id BIGINT,
  permission_id BIGINT,
  state TINYINT DEFAULT 1,
  update_time DATETIME,
  UNIQUE KEY uk_role_permissions_pair (role_id, permission_id),
  KEY idx_role_permissions_role_id (role_id),
  KEY idx_role_permissions_permission_id (permission_id),
  CONSTRAINT fk_role_permissions_role_id FOREIGN KEY (role_id) REFERENCES roles(id) ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_role_permissions_permission_id FOREIGN KEY (permission_id) REFERENCES permissions(id) ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE campus_zones (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  zone_name VARCHAR(128) UNIQUE,
  create_time DATETIME,
  update_time DATETIME,
  is_deleted TINYINT NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE locations (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  zone_id BIGINT,
  location_name VARCHAR(128),
  create_time DATETIME,
  update_time DATETIME,
  is_deleted TINYINT NOT NULL DEFAULT 0,
  UNIQUE KEY uk_locations_zone_name (zone_id, location_name),
  KEY idx_locations_zone_id (zone_id),
  CONSTRAINT fk_locations_zone_id FOREIGN KEY (zone_id) REFERENCES campus_zones(id) ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE species (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  species_name VARCHAR(128) UNIQUE,
  scientific_name VARCHAR(255) DEFAULT '',
  care_points TEXT,
  light_requirement VARCHAR(255) DEFAULT '',
  create_time DATETIME,
  update_time DATETIME,
  is_deleted TINYINT NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE plants (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  species_id BIGINT,
  location_id BIGINT,
  create_time DATETIME,
  update_time DATETIME,
  is_deleted TINYINT NOT NULL DEFAULT 0,
  KEY idx_plants_species_id (species_id),
  KEY idx_plants_location_id (location_id),
  CONSTRAINT fk_plants_species_id FOREIGN KEY (species_id) REFERENCES species(id) ON UPDATE CASCADE ON DELETE SET NULL,
  CONSTRAINT fk_plants_location_id FOREIGN KEY (location_id) REFERENCES locations(id) ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE species_images (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  species_id BIGINT,
  image_url VARCHAR(255) DEFAULT '',
  create_time DATETIME,
  update_time DATETIME,
  is_deleted TINYINT NOT NULL DEFAULT 0,
  KEY idx_species_images_species_id (species_id),
  CONSTRAINT fk_species_images_species_id FOREIGN KEY (species_id) REFERENCES species(id) ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE care_methods (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  method_name VARCHAR(128) UNIQUE,
  create_time DATETIME,
  update_time DATETIME,
  is_deleted TINYINT NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE care_rules (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  species_id BIGINT,
  care_method_id BIGINT,
  cycle_days INT DEFAULT 0,
  create_time DATETIME,
  update_time DATETIME,
  is_deleted TINYINT NOT NULL DEFAULT 0,
  UNIQUE KEY uk_care_rules_species_method (species_id, care_method_id, is_deleted),
  KEY idx_care_rules_species_id (species_id),
  KEY idx_care_rules_method_id (care_method_id),
  CONSTRAINT fk_care_rules_species_id FOREIGN KEY (species_id) REFERENCES species(id) ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_care_rules_method_id FOREIGN KEY (care_method_id) REFERENCES care_methods(id) ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE care_reminders (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  plant_id BIGINT,
  care_rule_id BIGINT,
  process_state TINYINT NOT NULL DEFAULT 1,
  is_valid TINYINT NOT NULL DEFAULT 1,
  create_time DATETIME,
  KEY idx_care_reminders_plant_id (plant_id),
  KEY idx_care_reminders_rule_id (care_rule_id),
  KEY idx_care_reminders_process_state (process_state),
  KEY idx_care_reminders_is_valid (is_valid),
  CONSTRAINT fk_care_reminders_plant_id FOREIGN KEY (plant_id) REFERENCES plants(id) ON UPDATE CASCADE ON DELETE SET NULL,
  CONSTRAINT fk_care_reminders_rule_id FOREIGN KEY (care_rule_id) REFERENCES care_rules(id) ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE care_records (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  reminder_id BIGINT,
  operator_user_id BIGINT,
  operation_status TINYINT DEFAULT 1,
  remark VARCHAR(255) DEFAULT '',
  snapshot_species_name VARCHAR(128) DEFAULT '',
  snapshot_zone_name VARCHAR(128) DEFAULT '',
  snapshot_location_name VARCHAR(128) DEFAULT '',
  snapshot_method_name VARCHAR(128) DEFAULT '',
  snapshot_cycle_days INT DEFAULT 0,
  create_time DATETIME,
  KEY idx_care_records_reminder_id (reminder_id),
  KEY idx_care_records_operator_user_id (operator_user_id),
  CONSTRAINT fk_care_records_reminder_id FOREIGN KEY (reminder_id) REFERENCES care_reminders(id) ON UPDATE CASCADE ON DELETE SET NULL,
  CONSTRAINT fk_care_records_operator_user_id FOREIGN KEY (operator_user_id) REFERENCES users(id) ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE feedback_types (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  type_name VARCHAR(128) UNIQUE,
  create_time DATETIME,
  update_time DATETIME
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE recognitions (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT,
  species_id BIGINT,
  image_url VARCHAR(255) DEFAULT '',
  create_time DATETIME,
  KEY idx_recognitions_user_id (user_id),
  KEY idx_recognitions_species_id (species_id),
  CONSTRAINT fk_recognitions_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON UPDATE CASCADE ON DELETE SET NULL,
  CONSTRAINT fk_recognitions_species_id FOREIGN KEY (species_id) REFERENCES species(id) ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE recognition_candidates (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  recognition_id BIGINT NULL,
  species_id BIGINT,
  confidence DOUBLE DEFAULT 0,
  cluster_id VARCHAR(128) DEFAULT '',
  KEY idx_recognition_candidates_recognition_id (recognition_id),
  KEY idx_recognition_candidates_species_id (species_id),
  CONSTRAINT fk_recognition_candidates_recognition_id FOREIGN KEY (recognition_id) REFERENCES recognitions(id) ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_recognition_candidates_species_id FOREIGN KEY (species_id) REFERENCES species(id) ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE feedbacks (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT,
  feedback_type_id BIGINT,
  recognition_id BIGINT NULL,
  content TEXT,
  audit_state TINYINT DEFAULT 1,
  audit_remark VARCHAR(255) DEFAULT '',
  create_time DATETIME,
  audit_time DATETIME,
  audited_by_user_id BIGINT,
  KEY idx_feedbacks_user_id (user_id),
  KEY idx_feedbacks_feedback_type_id (feedback_type_id),
  KEY idx_feedbacks_recognition_id (recognition_id),
  KEY idx_feedbacks_audited_by_user_id (audited_by_user_id),
  CONSTRAINT fk_feedbacks_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON UPDATE CASCADE ON DELETE SET NULL,
  CONSTRAINT fk_feedbacks_feedback_type_id FOREIGN KEY (feedback_type_id) REFERENCES feedback_types(id) ON UPDATE CASCADE ON DELETE SET NULL,
  CONSTRAINT fk_feedbacks_recognition_id FOREIGN KEY (recognition_id) REFERENCES recognitions(id) ON UPDATE CASCADE ON DELETE SET NULL,
  CONSTRAINT fk_feedbacks_audited_by_user_id FOREIGN KEY (audited_by_user_id) REFERENCES users(id) ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE operation_logs (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT,
  module_id BIGINT,
  operation_name VARCHAR(128) DEFAULT '',
  request_url VARCHAR(255) DEFAULT '',
  request_method VARCHAR(16) DEFAULT '',
  ip VARCHAR(64) DEFAULT '',
  ip_location VARCHAR(128) DEFAULT '',
  create_time DATETIME,
  KEY idx_operation_logs_user_id (user_id),
  KEY idx_operation_logs_module_id (module_id),
  CONSTRAINT fk_operation_logs_module_id FOREIGN KEY (module_id) REFERENCES modules(id) ON UPDATE CASCADE ON DELETE SET NULL,
  CONSTRAINT fk_operation_logs_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

SET FOREIGN_KEY_CHECKS = 1;
