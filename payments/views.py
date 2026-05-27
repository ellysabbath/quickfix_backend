# views.py

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import AllowAny
from .models import Transaction
from .serializers import (
    TransactionSerializer, InitiatePaymentSerializer,
    ManualPaymentSerializer, PaymentStatusSerializer, PaymentWebhookSerializer
)
from .services.payment_service import PaymentService

class PaymentViewSet(GenericViewSet):
    """ViewSet for payment operations"""
    permission_classes = [AllowAny]
    queryset = Transaction.objects.all()

    def get_serializer_class(self):
        if self.action == 'initiate':
            return InitiatePaymentSerializer
        elif self.action == 'manual':
            return ManualPaymentSerializer
        elif self.action == 'status':
            return PaymentStatusSerializer
        return TransactionSerializer

    @action(detail=False, methods=['post'])
    def initiate(self, request):
        """Initiate a new payment"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        result = PaymentService.initiate_payment(
            user=request.user,
            amount=data['amount'],
            payment_method=data['payment_method'],
            phone_number=data.get('phone_number'),
            booking_id=data.get('booking_id'),
            service_request_id=data.get('service_request_id')
        )

        if result.get('success'):
            return Response(result, status=status.HTTP_201_CREATED)
        return Response(result, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def manual(self, request):
        """Submit manual payment proof"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        result = PaymentService.confirm_manual_payment(
            transaction_id=data['transaction_id'],
            bank_reference=data['bank_reference'],
            payment_proof=request.FILES.get('payment_proof'),
            notes=data.get('notes')
        )

        if result.get('success'):
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def status(self, request):
        """Check payment status"""
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        result = PaymentService.get_payment_status(serializer.validated_data['transaction_id'])

        if result.get('success'):
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'])
    def history(self, request):
        """Get user's payment history"""
        transactions = Transaction.objects.filter(user=request.user).order_by('-created_at')
        serializer = TransactionSerializer(transactions, many=True)
        return Response({
            'success': True,
            'count': transactions.count(),
            'results': serializer.data
        })

    @action(detail=False, methods=['post'], permission_classes=[])
    def webhook(self, request):
        """Webhook endpoint for payment providers (no auth)"""
        serializer = PaymentWebhookSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = PaymentService.process_webhook(request.data)

        if result.get('success'):
            return Response({'ResultCode': 0, 'ResultDesc': 'Success'}, status=status.HTTP_200_OK)
        return Response({'ResultCode': 1, 'ResultDesc': 'Failed'}, status=status.HTTP_200_OK)