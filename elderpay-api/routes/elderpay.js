const express = require('express');
const router = express.Router();
const elderPayController = require('../controllers/elderPayController');

// Create payment order
router.post('/create', elderPayController.createOrder);

// Check order status
router.get('/check/:order_id', elderPayController.checkOrder);

// Get all pending orders (for background checker)
router.get('/pending', elderPayController.getPendingOrders);

module.exports = router;
