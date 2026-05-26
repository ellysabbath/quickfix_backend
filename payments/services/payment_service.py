# services/payment_service.py

import uuid
import hashlib
import base64
import requests
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from rest_framework import status
from ..models import Transaction, PaymentSession, PaymentWebhook, PaymentStatus, PaymentMethod

class PaymentService:
    """Handle all payment operations"""
    
    @staticmethod
    def initiate_payment(user, amount, payment_method, phone_number=None, booking_id=None, service_request_id=None):
        """Initiate a new payment"""
        
        # Create transaction record
        transaction = Transaction.objects.create(
            user=user,
            amount=amount,
            payment_method=payment_method,
            payment_status=PaymentStatus.PENDING,
            phone_number=phone_number if payment_method != PaymentMethod.MANUAL else None,
            booking_id=booking_id,
            service_request_id=service_request_id
        )
        
        # For mobile money, initiate STK Push
        if payment_method in [PaymentMethod.MPESA, PaymentMethod.TIGO_PESA, PaymentMethod.AIRTEL_MONEY, PaymentMethod.HALO_PESA]:
            session = PaymentService._initiate_stk_push(transaction, phone_number)
            return {
                'success': True,
                'transaction_id': transaction.transaction_id,
                'session_id': session.session_id,
                'checkout_request_id': session.checkout_request_id,
                'message': f'Payment initiated. Check your phone for the prompt.'
            }
        
        # For manual payment, return bank details
        elif payment_method == PaymentMethod.MANUAL:
            return {
                'success': True,
                'transaction_id': transaction.transaction_id,
                'bank_details': PaymentService._get_bank_details(),
                'message': 'Please complete payment using bank deposit'
            }
        
        return {'success': False, 'error': 'Invalid payment method'}
    
    @staticmethod
    def _initiate_stk_push(transaction, phone_number):
        """Initiate STK Push to customer's phone"""
        
        # Create payment session
        session = PaymentSession.objects.create(
            session_id=f"SESS-{uuid.uuid4().hex[:12].upper()}",
            transaction=transaction,
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        
        # Format phone number (remove leading 0 or +)
        formatted_phone = phone_number.lstrip('+').lstrip('0')
        
        # For M-Pesa (example - integrate with actual API)
        if transaction.payment_method == PaymentMethod.MPESA:
            # Here you would integrate with M-Pesa API
            # Example using Daraja API (Safaricom)
            checkout_id = f"CHECKOUT-{uuid.uuid4().hex[:10].upper()}"
            session.checkout_request_id = checkout_id
            session.save()
            
            # Simulate API call
            # response = PaymentService._call_mpesa_stk_push(formatted_phone, transaction.amount, checkout_id)
        
        # For Tigo Pesa
        elif transaction.payment_method == PaymentMethod.TIGO_PESA:
            # Integrate with Tigo Pesa API
            pass
        
        # For Airtel Money
        elif transaction.payment_method == PaymentMethod.AIRTEL_MONEY:
            # Integrate with Airtel Money API
            pass
        
        # For Halo Pesa
        elif transaction.payment_method == PaymentMethod.HALO_PESA:
            # Integrate with Halo Pesa API
            pass
        
        return session
    
    @staticmethod
    def _get_bank_details():
        """Get bank account details for manual payment"""
        return {
            'bank_name': 'CRDB Bank PLC',
            'account_name': 'QuickFix Services',
            'account_number': '01-1234567890',
            'branch': 'Kariakoo Branch',
            'swift_code': 'CORUTZTZ'
        }
    
    @staticmethod
    def confirm_manual_payment(transaction_id, bank_reference, payment_proof=None, notes=None):
        """Confirm manual payment after user submits proof"""
        try:
            transaction = Transaction.objects.get(transaction_id=transaction_id)
            
            if transaction.payment_status != PaymentStatus.PENDING:
                return {'success': False, 'error': 'Payment already processed'}
            
            transaction.bank_reference = bank_reference
            transaction.payment_status = PaymentStatus.PROCESSING
            transaction.notes = notes
            transaction.save()
            
            # In production, you might want to send notification to admin for verification
            
            return {
                'success': True,
                'message': 'Payment proof received. Will be verified within 24 hours.',
                'transaction_id': transaction.transaction_id
            }
            
        except Transaction.DoesNotExist:
            return {'success': False, 'error': 'Transaction not found'}
    
    @staticmethod
    def get_payment_status(transaction_id):
        """Get payment status for a transaction"""
        try:
            transaction = Transaction.objects.get(transaction_id=transaction_id)
            return {
                'success': True,
                'transaction_id': transaction.transaction_id,
                'status': transaction.payment_status,
                'status_display': dict(PaymentStatus.choices).get(transaction.payment_status),
                'amount': transaction.amount,
                'payment_method': dict(PaymentMethod.choices).get(transaction.payment_method),
                'created_at': transaction.created_at,
                'completed_at': transaction.completed_at
            }
        except Transaction.DoesNotExist:
            return {'success': False, 'error': 'Transaction not found'}
    
    @staticmethod
    def complete_payment(transaction_id, provider_reference=None):
        """Mark payment as completed (usually called by webhook)"""
        try:
            transaction = Transaction.objects.get(transaction_id=transaction_id)
            transaction.payment_status = PaymentStatus.COMPLETED
            transaction.provider_reference = provider_reference
            transaction.completed_at = timezone.now()
            transaction.save()
            
            # Update associated booking/service request status
            if transaction.booking_id:
                # Update booking status
                pass
            if transaction.service_request_id:
                # Update service request status
                pass
            
            return {'success': True}
        except Transaction.DoesNotExist:
            return {'success': False, 'error': 'Transaction not found'}
    
    @staticmethod
    def process_webhook(data):
        """Process incoming webhook from payment provider"""
        webhook = PaymentWebhook.objects.create(payload=data)
        
        # Extract transaction ID from webhook data
        transaction_id = data.get('transaction_id') or data.get('TransID')
        checkout_request_id = data.get('checkout_request_id') or data.get('CheckoutRequestID')
        result_code = data.get('result_code') or data.get('ResultCode')
        
        if result_code == 0:  # Success
            # Find transaction by checkout ID
            try:
                session = PaymentSession.objects.get(checkout_request_id=checkout_request_id)
                transaction = session.transaction
                PaymentService.complete_payment(transaction.transaction_id, data.get('provider_reference'))
                webhook.processed = True
                webhook.processed_at = timezone.now()
                webhook.transaction_id = transaction.transaction_id
                webhook.save()
                return {'success': True}
            except PaymentSession.DoesNotExist:
                pass
        
        webhook.save()
        return {'success': False, 'error': 'Webhook processing failed'}