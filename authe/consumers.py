import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class UserConsumer(AsyncWebsocketConsumer):
    """Consumer for user-specific notifications (calls, status updates, etc.)"""
    
    async def connect(self):
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.user = self.scope['user']
        
        # Verify authentication
        if not self.user.is_authenticated or str(self.user.id) != self.user_id:
            await self.close()
            return
        
        self.room_group_name = f'user_{self.user_id}'
        
        # Join user room
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Update user online status
        await self.set_user_online(True)
    
    async def disconnect(self, close_code):
        # Update user online status
        await self.set_user_online(False)
        
        # Leave user room
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get('type')
        
        if message_type == 'ping':
            await self.send(text_data=json.dumps({
                'type': 'pong',
                'timestamp': timezone.now().isoformat()
            }))
    
    async def incoming_call(self, event):
        """Send incoming call notification to user"""
        await self.send(text_data=json.dumps({
            'type': 'incoming_call',
            'call_id': event.get('call_id'),
            'caller_id': event.get('caller_id'),
            'caller_name': event.get('caller_name'),
            'call_type': event.get('call_type')
        }))
    
    async def call_status_update(self, event):
        """Send call status update to user"""
        await self.send(text_data=json.dumps({
            'type': 'call_status_update',
            'call_id': event.get('call_id'),
            'status': event.get('status'),
            'duration': event.get('duration', 0)
        }))
    
    async def new_message(self, event):
        """Send new message notification to user"""
        await self.send(text_data=json.dumps({
            'type': 'new_message',
            'chat_id': event.get('chat_id'),
            'message': event.get('message')
        }))
    
    async def user_status_change(self, event):
        """Notify when a contact's online status changes"""
        await self.send(text_data=json.dumps({
            'type': 'user_status',
            'user_id': event.get('user_id'),
            'is_online': event.get('is_online')
        }))
    
    @database_sync_to_async
    def set_user_online(self, is_online):
        """Set user online status (you need to add an 'is_online' field to User model)"""
        try:
            user = User.objects.get(id=self.user_id)
            user.is_online = is_online
            user.last_seen = timezone.now()
            user.save()
            
            # Notify contacts about status change
            from chat.models import Contact
            contacts = Contact.objects.filter(contact_user=user)
            for contact in contacts:
                # Send WebSocket to each contact
                from channels.layers import get_channel_layer
                from asgiref.sync import async_to_sync
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f'user_{contact.user.id}',
                    {
                        'type': 'user_status_change',
                        'user_id': user.id,
                        'is_online': is_online
                    }
                )
        except User.DoesNotExist:
            pass