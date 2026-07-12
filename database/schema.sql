-- schema.sql
-- PaperTrader Database Schema (MySQL)

CREATE DATABASE IF NOT EXISTS papertrader;
USE papertrader;

-- Users: identity and credentials
CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    balance DECIMAL(15,2) NOT NULL DEFAULT 100000.00,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
 
-- Holdings: current stock positions per user
CREATE TABLE IF NOT EXISTS holdings (
    holding_key INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    stock_name VARCHAR(20) NOT NULL,
    quantity INT NOT NULL,
    avg_buy_price DECIMAL(15,2) NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_stock (user_id, stock_name)
);

-- Transactions: immutable record of every executed trade
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    stock_name VARCHAR(20) NOT NULL,
    transaction_type ENUM('BUY', 'SELL') NOT NULL,
    quantity INT NOT NULL,
    price DECIMAL(15,2) NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);