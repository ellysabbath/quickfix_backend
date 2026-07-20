# payments/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import PaymentMethod, PaymentRecord, BankDetails, PaymentNotification
from .serializers import (
    PaymentMethodSerializer, PaymentRecordSerializer,
    PaymentRecordCreateSerializer, PaymentRecordUpdateSerializer,
    BankDetailsSerializer, CustomerServiceRequestSerializer
)
from .services import EmailService

import logging
import uuid

logger = logging.getLogger(__name__)




class PaymentMethodViewSet(viewsets.ModelViewSet):
    """
    ViewSet for PaymentMethod - No authentication required
    URL: /api/pay/payment-methods/
    """
    queryset = PaymentMethod.objects.filter(is_active=True)
    serializer_class = PaymentMethodSerializer
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['get'], url_path='active')
    def active(self, request):
        """Get active payment methods"""
        active_methods = self.get_queryset()
        serializer = self.get_serializer(active_methods, many=True)
        return Response(serializer.data)


class BankDetailsViewSet(viewsets.ModelViewSet):
    """
    ViewSet for BankDetails - No authentication required
    URL: /api/pay/bank-details/
    """
    queryset = BankDetails.objects.filter(is_active=True)
    serializer_class = BankDetailsSerializer
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['get'], url_path='current')
    def current(self, request):
        """Get current active bank details"""
        bank_details = self.get_queryset().first()
        if bank_details:
            serializer = self.get_serializer(bank_details)
            return Response(serializer.data)
        return Response({'error': 'No bank details found'}, status=status.HTTP_404_NOT_FOUND)


class PaymentRecordViewSet(viewsets.ModelViewSet):
    """
    ViewSet for PaymentRecord - No authentication required
    URL: /api/pay/payment-records/
    """
    queryset = PaymentRecord.objects.all()
    serializer_class = PaymentRecordSerializer
    permission_classes = [AllowAny]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return PaymentRecordCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return PaymentRecordUpdateSerializer
        return PaymentRecordSerializer
    
    def get_queryset(self):
        """Filter by phone number if provided"""
        queryset = super().get_queryset()
        phone = self.request.query_params.get('phone')
        if phone:
            queryset = queryset.filter(sender_phone=phone)
        return queryset
    
    def create(self, request, *args, **kwargs):
        """Create a new payment record with email notification"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        payment = serializer.save()
        
        # Send email notification for payment initiation
        try:
            email_service = EmailService()
            email_service.send_payment_initiated_email(payment)
            logger.info(f"Payment initiation email sent to {payment.sender_email}")
        except Exception as e:
            logger.error(f"Failed to send payment initiation email: {e}")
        
        response_serializer = PaymentRecordSerializer(payment)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'], url_path='my_payments')
    def my_payments(self, request):
        """Get payments for a specific phone number"""
        phone = request.query_params.get('phone')
        if phone:
            payments = self.get_queryset().filter(sender_phone=phone)
        else:
            payments = self.get_queryset()
        serializer = self.get_serializer(payments, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='pending')
    def pending(self, request):
        """Get pending payments"""
        pending_payments = self.get_queryset().filter(status='pending')
        serializer = self.get_serializer(pending_payments, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['patch'], url_path='confirm')
    def confirm(self, request, pk=None):
        """Confirm a payment with email notification"""
        payment = self.get_object()
        
        if payment.status in ['confirmed', 'verified', 'completed']:
            return Response(
                {'error': 'Payment already confirmed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = PaymentRecordUpdateSerializer(
            payment,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            old_status = payment.status
            payment = serializer.save()
            
            # Generate transaction ID if not present
            if not payment.transaction_id:
                payment.transaction_id = f"TX-{timezone.now().strftime('%Y%m%d')}-{str(uuid.uuid4()).upper()[:8]}"
                payment.save()
            
            # Send email confirmation
            try:
                email_service = EmailService()
                email_service.send_payment_confirmation_email(payment)
                logger.info(f"Payment confirmation email sent to {payment.sender_email}")
            except Exception as e:
                logger.error(f"Failed to send payment confirmation email: {e}")
            
            return Response(PaymentRecordSerializer(payment).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], url_path='initiate_payment')
    def initiate_payment(self, request, pk=None):
        """Initiate a payment (for mobile money)"""
        payment = self.get_object()
        
        transaction_id = f"TX-{timezone.now().strftime('%Y%m%d')}-{str(uuid.uuid4()).upper()[:8]}"
        payment.transaction_id = transaction_id
        payment.status = 'pending'
        payment.save()
        
        return Response({
            'success': True,
            'transaction_id': transaction_id,
            'payment_id': payment.payment_id,
            'message': 'Payment initiated successfully'
        })
    
    @action(detail=True, methods=['post'], url_path='submit_manual')
    def submit_manual(self, request, pk=None):
        """Submit manual payment (bank deposit)"""
        payment = self.get_object()
        
        transaction_reference = request.data.get('transaction_reference')
        proof_uri = request.data.get('proof_uri')
        proof_filename = request.data.get('proof_filename')
        notes = request.data.get('notes', '')
        
        if not transaction_reference:
            return Response(
                {'error': 'Transaction reference is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        payment.transaction_reference = transaction_reference
        if proof_uri:
            payment.proof_uri = proof_uri
            payment.proof_filename = proof_filename
        payment.status = 'confirmed'
        payment.status_display = 'Confirmed'
        payment.confirmed_at = timezone.now()
        payment.save()
        
        # Send email confirmation
        try:
            email_service = EmailService()
            email_service.send_payment_confirmation_email(payment)
            logger.info(f"Manual payment confirmation email sent to {payment.sender_email}")
        except Exception as e:
            logger.error(f"Failed to send manual payment confirmation email: {e}")
        
        return Response({
            'success': True,
            'message': 'Manual payment submitted successfully',
            'payment': PaymentRecordSerializer(payment).data
        })
    
    @action(detail=True, methods=['post'], url_path='verify')
    def verify(self, request, pk=None):
        """Verify a payment (admin only)"""
        payment = self.get_object()
        
        if payment.status in ['verified', 'completed']:
            return Response(
                {'error': 'Payment already verified or completed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        old_status = payment.status
        payment.status = 'verified'
        payment.verified_at = timezone.now()
        payment.save()
        
        # Send verification email
        try:
            email_service = EmailService()
            email_service.send_payment_verified_email(payment)
            logger.info(f"Payment verification email sent to {payment.sender_email}")
        except Exception as e:
            logger.error(f"Failed to send payment verification email: {e}")
        
        return Response({
            'success': True,
            'message': 'Payment verified successfully',
            'payment': PaymentRecordSerializer(payment).data
        })
    
    @action(detail=True, methods=['post'], url_path='complete')
    def complete(self, request, pk=None):
        """Complete a payment (admin only)"""
        payment = self.get_object()
        
        if payment.status == 'completed':
            return Response(
                {'error': 'Payment already completed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        old_status = payment.status
        payment.status = 'completed'
        payment.save()
        
        # Send congratulations email
        try:
            email_service = EmailService()
            email_service.send_congratulations_email(payment)
            logger.info(f"Congratulations email sent to {payment.sender_email}")
        except Exception as e:
            logger.error(f"Failed to send congratulations email: {e}")
        
        # Update service request status if exists
        if payment.service_request:
            payment.service_request.request_status = 'completed'
            payment.service_request.save()
        
        return Response({
            'success': True,
            'message': 'Payment completed successfully',
            'payment': PaymentRecordSerializer(payment).data
        })
    
    @action(detail=True, methods=['post'], url_path='notify_whatsapp')
    def notify_whatsapp(self, request, pk=None):
        """Mark WhatsApp notification as sent"""
        payment = self.get_object()
        payment.whatsapp_sent = True
        payment.save()
        return Response({'status': 'WhatsApp notification marked as sent'})


class PaymentStatusViewSet(viewsets.ViewSet):
    """
    ViewSet for checking payment status
    URL: /api/pay/payment-status/check/
    """
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['get'], url_path='check')
    def check(self, request):
        """Check payment status by transaction ID"""
        transaction_id = request.query_params.get('transaction_id')
        if not transaction_id:
            return Response(
                {'error': 'Transaction ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            payment = PaymentRecord.objects.get(transaction_id=transaction_id)
            return Response({
                'status': payment.status,
                'status_display': payment.status_display,
                'payment_id': payment.payment_id,
                'amount': str(payment.amount),
                'sender_name': payment.sender_name,
                'created_at': payment.created_at,
                'transaction_id': payment.transaction_id,
                'transaction_reference': payment.transaction_reference
            })
        except PaymentRecord.DoesNotExist:
            return Response(
                {'error': 'Payment not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class PaymentNotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for PaymentNotification
    URL: /api/pay/payment-notifications/
    """
    queryset = PaymentNotification.objects.all()
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        """Filter by payment record if provided"""
        queryset = super().get_queryset()
        payment_record_id = self.request.query_params.get('payment_record')
        if payment_record_id:
            queryset = queryset.filter(payment_record_id=payment_record_id)
        return queryset
    
    @action(detail=False, methods=['post'], url_path='send_status_update')
    def send_status_update(self, request):
        """Send status update notification"""
        payment_id = request.data.get('payment_id')
        new_status = request.data.get('status')
        notes = request.data.get('notes', '')
        
        if not payment_id or not new_status:
            return Response(
                {'error': 'Payment ID and status are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            payment = PaymentRecord.objects.get(payment_id=payment_id)
            old_status = payment.status
            
            email_service = EmailService()
            email_service.send_status_update_email(payment, old_status, new_status)
            
            return Response({
                'success': True,
                'message': 'Status update email sent'
            })
        except PaymentRecord.DoesNotExist:
            return Response(
                {'error': 'Payment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error sending status update: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )