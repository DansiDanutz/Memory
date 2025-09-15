#!/usr/bin/env python3
"""
Payment Service for Memory App - Stripe Integration
Handles subscription management and payment processing
"""
import os
import logging
import stripe
from datetime import datetime
from typing import Dict, Any, Optional
from memory_app import UserPlan, CreditManager

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Stripe
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
if STRIPE_SECRET_KEY and not STRIPE_SECRET_KEY.startswith('pk_'):
    stripe.api_key = STRIPE_SECRET_KEY
    logger.info("✅ Stripe initialized with secret key")
else:
    stripe.api_key = None
    if STRIPE_SECRET_KEY and STRIPE_SECRET_KEY.startswith('pk_'):
        logger.warning("⚠️ Stripe running in DEMO mode - publishable key detected")
    else:
        logger.warning("⚠️ Stripe running in DEMO mode - no secret key configured")

# Get domain for webhooks
YOUR_DOMAIN = os.environ.get('REPLIT_DEV_DOMAIN') if os.environ.get('REPLIT_DEPLOYMENT') != '' else os.environ.get('REPLIT_DOMAINS', '').split(',')[0] if os.environ.get('REPLIT_DOMAINS') else 'localhost:5000'

class PaymentService:
    """Handles Stripe payment processing for Memory App subscriptions"""
    
    def __init__(self):
        # Stripe Price IDs (these would be configured in Stripe Dashboard)
        self.price_ids = {
            UserPlan.PAID.value: 'price_paid_monthly',  # Replace with actual Stripe Price ID
            UserPlan.PRO.value: 'price_pro_monthly'     # Replace with actual Stripe Price ID
        }
        
        self.credit_manager = CreditManager()
    
    def create_checkout_session(
        self, 
        plan: UserPlan, 
        user_id: str,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create Stripe checkout session for plan upgrade"""
        
        if plan == UserPlan.FREE:
            return {
                'success': False,
                'message': 'Cannot create checkout session for free plan'
            }
        
        try:
            price_id = self.price_ids.get(plan.value)
            if not price_id:
                return {
                    'success': False,
                    'message': f'Price ID not configured for {plan.value} plan'
                }
            
            # Default URLs
            if not success_url:
                success_url = f'https://{YOUR_DOMAIN}/payment/success'
            if not cancel_url:
                cancel_url = f'https://{YOUR_DOMAIN}/payment/cancel'
            
            plan_details = self.credit_manager.get_plan_details(plan)
            
            checkout_session = stripe.checkout.Session.create(
                line_items=[
                    {
                        'price': price_id,
                        'quantity': 1,
                    },
                ],
                mode='subscription',
                success_url=f'{success_url}?session_id={{CHECKOUT_SESSION_ID}}',
                cancel_url=cancel_url,
                automatic_tax={'enabled': False},
                metadata={
                    'user_id': user_id,
                    'plan': plan.value,
                    'credits': str(plan_details['memories'])
                },
                subscription_data={
                    'metadata': {
                        'user_id': user_id,
                        'plan': plan.value
                    }
                }
            )
            
            logger.info(f"💳 Created checkout session for user {user_id}, plan {plan.value}")
            
            return {
                'success': True,
                'checkout_url': checkout_session.url,
                'session_id': checkout_session.id,
                'plan': plan.value,
                'price': str(plan_details['price'])
            }
            
        except Exception as e:
            logger.error(f"Checkout session creation failed: {e}")
            return {
                'success': False,
                'message': f'Payment setup failed: {str(e)}'
            }
    
    def handle_webhook(self, payload: str, sig_header: str) -> Dict[str, Any]:
        """Handle Stripe webhook events"""
        
        try:
            # Verify webhook signature (in production, use your webhook secret)
            webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
            if webhook_secret:
                event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
            else:
                # For development - parse without verification
                import json
                event = json.loads(payload)
            
            logger.info(f"🔔 Received Stripe webhook: {event['type']}")
            
            # Handle successful payment
            if event['type'] == 'checkout.session.completed':
                session = event['data']['object']
                return self._handle_successful_payment(session)
            
            # Handle subscription updates
            elif event['type'] == 'customer.subscription.updated':
                subscription = event['data']['object']
                return self._handle_subscription_update(subscription)
            
            # Handle failed payments
            elif event['type'] == 'invoice.payment_failed':
                invoice = event['data']['object']
                return self._handle_payment_failure(invoice)
            
            return {'success': True, 'message': 'Webhook processed'}
            
        except Exception as e:
            logger.error(f"Webhook processing failed: {e}")
            return {
                'success': False,
                'message': f'Webhook error: {str(e)}'
            }
    
    def _handle_successful_payment(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Process successful payment and upgrade user"""
        
        try:
            user_id = session['metadata'].get('user_id')
            plan_name = session['metadata'].get('plan')
            
            if not user_id or not plan_name:
                logger.error("Missing user_id or plan in session metadata")
                return {'success': False, 'message': 'Invalid session metadata'}
            
            # Convert plan name to enum
            plan = UserPlan[plan_name.upper()]
            
            # Import memory app to upgrade user
            from memory_app import memory_app
            
            # Update user's subscription details
            if user_id in memory_app.voice_auth.user_accounts:
                user = memory_app.voice_auth.user_accounts[user_id]
                
                # Store Stripe customer and subscription IDs
                user.stripe_customer_id = session.get('customer')
                user.stripe_subscription_id = session.get('subscription')
                
                # Upgrade the user's plan
                upgrade_result = memory_app.credit_manager.upgrade_user_plan(user, plan)
                
                if upgrade_result['success']:
                    logger.info(f"🎉 Successfully upgraded user {user_id} to {plan_name} plan")
                    return {
                        'success': True,
                        'message': f'User {user_id} upgraded to {plan_name} plan',
                        'upgrade_result': upgrade_result
                    }
            
            logger.error(f"User {user_id} not found in voice auth system")
            return {'success': False, 'message': 'User not found'}
            
        except Exception as e:
            logger.error(f"Payment processing failed: {e}")
            return {
                'success': False,
                'message': f'Payment processing error: {str(e)}'
            }
    
    def _handle_subscription_update(self, subscription: Dict[str, Any]) -> Dict[str, Any]:
        """Handle subscription status changes"""
        
        try:
            user_id = subscription['metadata'].get('user_id')
            status = subscription.get('status')
            
            logger.info(f"📊 Subscription update for user {user_id}: status={status}")
            
            # Handle subscription cancellation or expiration
            if status in ['canceled', 'unpaid', 'past_due']:
                # Could implement logic to downgrade user to free plan
                pass
            
            return {'success': True, 'message': 'Subscription updated'}
            
        except Exception as e:
            logger.error(f"Subscription update failed: {e}")
            return {'success': False, 'message': str(e)}
    
    def _handle_payment_failure(self, invoice: Dict[str, Any]) -> Dict[str, Any]:
        """Handle failed payment attempts"""
        
        try:
            # Extract user information from invoice
            customer_id = invoice.get('customer')
            
            logger.warning(f"💳 Payment failed for customer {customer_id}")
            
            # Could implement logic to:
            # 1. Notify user of payment failure
            # 2. Provide grace period
            # 3. Downgrade after multiple failures
            
            return {'success': True, 'message': 'Payment failure processed'}
            
        except Exception as e:
            logger.error(f"Payment failure handling failed: {e}")
            return {'success': False, 'message': str(e)}
    
    def get_customer_portal_url(self, customer_id: str) -> Dict[str, Any]:
        """Create customer portal session for subscription management"""
        
        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=f'https://{YOUR_DOMAIN}/'
            )
            
            return {
                'success': True,
                'portal_url': session.url
            }
            
        except Exception as e:
            logger.error(f"Customer portal creation failed: {e}")
            return {
                'success': False,
                'message': f'Portal creation failed: {str(e)}'
            }

# Global instance
payment_service = PaymentService()