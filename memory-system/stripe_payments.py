#!/usr/bin/env python3
"""
Stripe Payment Integration for Digital Immortality Platform
Handles subscriptions, billing, and credit management
"""

import os
import stripe
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum
import json

logger = logging.getLogger(__name__)

# Initialize Stripe - Handle incorrect key configuration
# The environment has a publishable key, we need a secret key for API calls
STRIPE_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
# If the key starts with 'pk_', it's a publishable key - use demo mode
if not STRIPE_KEY or STRIPE_KEY.startswith('pk_'):
    # Running in demo mode - no real Stripe API calls
    stripe.api_key = None
    DEMO_MODE = True
    if STRIPE_KEY and STRIPE_KEY.startswith('pk_'):
        logger.warning("⚠️ Stripe running in DEMO mode - publishable key detected")
    else:
        logger.warning("⚠️ Stripe running in DEMO mode - no secret key configured")
else:
    stripe.api_key = STRIPE_KEY
    DEMO_MODE = False
    logger.info("✅ Stripe initialized with secret key")

class SubscriptionTier(Enum):
    """Subscription tiers with pricing"""
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ELITE = "elite"

class StripePayments:
    """Complete Stripe payment integration"""
    
    def __init__(self):
        self.stripe_key = os.environ.get('STRIPE_SECRET_KEY', '')
        self.webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
        self.initialized = False
        
        # Pricing configuration (in cents)
        self.pricing = {
            SubscriptionTier.FREE: {
                'price': 0,
                'credits': 50,
                'name': 'Free Tier',
                'description': 'Basic memory storage',
                'features': [
                    '50 memories per month',
                    'Text-only memories',
                    'Basic categories',
                    'Email support'
                ]
            },
            SubscriptionTier.BASIC: {
                'price': 999,  # $9.99
                'credits': 200,
                'stripe_price_id': '',
                'name': 'Basic',
                'description': 'Enhanced memory features',
                'features': [
                    '200 memories per month',
                    'Voice notes',
                    'Smart commitments',
                    'Contact profiles',
                    'Priority support'
                ]
            },
            SubscriptionTier.PRO: {
                'price': 1999,  # $19.99
                'credits': 500,
                'stripe_price_id': '',
                'name': 'Pro',
                'description': 'Full AI-powered features',
                'features': [
                    '500 memories per month',
                    'AI avatars',
                    'Secret vaults',
                    'Voice calls',
                    'Family sharing',
                    'Advanced analytics'
                ]
            },
            SubscriptionTier.ELITE: {
                'price': 3999,  # $39.99
                'credits': 1000,
                'stripe_price_id': '',
                'name': 'Elite',
                'description': 'Digital immortality',
                'features': [
                    'Unlimited memories',
                    'Custom AI avatars',
                    'Inheritance system',
                    'White-glove support',
                    'API access',
                    'Data export',
                    'Voice cloning'
                ]
            }
        }
        
        self.initialize_stripe()
    
    def initialize_stripe(self):
        """Initialize Stripe and create products/prices"""
        global DEMO_MODE
        
        if DEMO_MODE or not self.stripe_key or self.stripe_key.startswith('pk_'):
            logger.warning("⚠️ Stripe running in DEMO mode - payment features simulated")
            self.initialized = True  # Set to True for demo mode
            stripe.api_key = None  # Ensure no API key is set in demo mode
            return
        
        # Only set API key if we have a valid secret key
        stripe.api_key = self.stripe_key
        
        try:
            # Test API key
            stripe.Account.retrieve()
            self.initialized = True
            logger.info("✅ Stripe initialized successfully")
            
            # Create products and prices
            self.setup_products_and_prices()
            
        except stripe.error.AuthenticationError:
            logger.error("❌ Invalid Stripe API key - switching to DEMO mode")
            self.initialized = True  # Enable demo mode on auth failure
            DEMO_MODE = True
        except Exception as e:
            logger.error(f"❌ Failed to initialize Stripe: {e}")
            self.initialized = False
    
    def setup_products_and_prices(self):
        """Create Stripe products and prices for each tier"""
        if not self.initialized:
            return
        
        try:
            # Create or update main product
            products = stripe.Product.list(limit=100)
            memory_product = None
            
            for product in products:
                if product.metadata.get('app') == 'digital_immortality':
                    memory_product = product
                    break
            
            if not memory_product:
                memory_product = stripe.Product.create(
                    name="Digital Immortality Platform",
                    description="AI-powered memory preservation system",
                    metadata={'app': 'digital_immortality'}
                )
                logger.info(f"✅ Created Stripe product: {memory_product.id}")
            
            # Create prices for each paid tier
            for tier in [SubscriptionTier.BASIC, SubscriptionTier.PRO, SubscriptionTier.ELITE]:
                tier_config = self.pricing[tier]
                
                # Check if price already exists
                prices = stripe.Price.list(
                    product=memory_product.id,
                    limit=100
                )
                
                existing_price = None
                for price in prices:
                    if price.metadata.get('tier') == tier.value:
                        existing_price = price
                        break
                
                if not existing_price:
                    # Create new price
                    price = stripe.Price.create(
                        product=memory_product.id,
                        unit_amount=tier_config['price'],
                        currency='usd',
                        recurring={'interval': 'month'},
                        metadata={'tier': tier.value}
                    )
                    tier_config['stripe_price_id'] = price.id
                    logger.info(f"✅ Created price for {tier.value}: {price.id}")
                else:
                    tier_config['stripe_price_id'] = existing_price.id
                    logger.info(f"✅ Using existing price for {tier.value}: {existing_price.id}")
        
        except Exception as e:
            logger.error(f"❌ Failed to setup products/prices: {e}")
    
    async def create_customer(self, user_id: str, email: str, name: Optional[str] = None) -> Optional[str]:
        """Create Stripe customer"""
        if not self.initialized:
            return None
        
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata={
                    'user_id': user_id,
                    'platform': 'digital_immortality'
                }
            )
            
            logger.info(f"✅ Created Stripe customer: {customer.id}")
            return customer.id
            
        except Exception as e:
            logger.error(f"❌ Failed to create customer: {e}")
            return None
    
    async def create_subscription(
        self,
        customer_id: str,
        tier: SubscriptionTier,
        trial_days: int = 7
    ) -> Optional[Dict[str, Any]]:
        """Create subscription for customer"""
        if not self.initialized or tier == SubscriptionTier.FREE:
            return None
        
        tier_config = self.pricing[tier]
        price_id = tier_config.get('stripe_price_id')
        
        if not price_id:
            logger.error(f"❌ No price ID for tier {tier.value}")
            return None
        
        try:
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{'price': price_id}],
                trial_period_days=trial_days,
                payment_behavior='default_incomplete',
                payment_settings={'save_default_payment_method': 'on_subscription'},
                expand=['latest_invoice.payment_intent'],
                metadata={'tier': tier.value}
            )
            
            logger.info(f"✅ Created subscription: {subscription.id}")
            
            return {
                'subscription_id': subscription.id,
                'status': subscription.status,
                'client_secret': subscription.latest_invoice.payment_intent.client_secret if subscription.latest_invoice else None,
                'trial_end': subscription.trial_end
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to create subscription: {e}")
            return None
    
    async def cancel_subscription(self, subscription_id: str, immediate: bool = False) -> bool:
        """Cancel subscription"""
        if not self.initialized:
            return False
        
        try:
            if immediate:
                stripe.Subscription.delete(subscription_id)
                logger.info(f"✅ Subscription {subscription_id} cancelled immediately")
            else:
                stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True
                )
                logger.info(f"✅ Subscription {subscription_id} set to cancel at period end")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to cancel subscription: {e}")
            return False
    
    async def update_subscription(self, subscription_id: str, new_tier: SubscriptionTier) -> bool:
        """Update subscription to new tier"""
        if not self.initialized or new_tier == SubscriptionTier.FREE:
            return False
        
        tier_config = self.pricing[new_tier]
        price_id = tier_config.get('stripe_price_id')
        
        if not price_id:
            logger.error(f"❌ No price ID for tier {new_tier.value}")
            return False
        
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            
            # Update subscription item with new price
            stripe.Subscription.modify(
                subscription_id,
                items=[{
                    'id': subscription['items']['data'][0].id,
                    'price': price_id
                }],
                metadata={'tier': new_tier.value}
            )
            
            logger.info(f"✅ Updated subscription {subscription_id} to {new_tier.value}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update subscription: {e}")
            return False
    
    async def create_payment_intent(self, amount: int, customer_id: str, description: str) -> Optional[Dict[str, Any]]:
        """Create one-time payment intent for credits"""
        if not self.initialized:
            return None
        
        try:
            intent = stripe.PaymentIntent.create(
                amount=amount,  # Amount in cents
                currency='usd',
                customer=customer_id,
                description=description,
                metadata={'type': 'credits_purchase'}
            )
            
            logger.info(f"✅ Created payment intent: {intent.id}")
            
            return {
                'intent_id': intent.id,
                'client_secret': intent.client_secret,
                'amount': amount
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to create payment intent: {e}")
            return None
    
    async def process_webhook(self, payload: bytes, signature: str) -> Dict[str, Any]:
        """Process Stripe webhook events"""
        if not self.initialized or not self.webhook_secret:
            return {'success': False, 'error': 'Not configured'}
        
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, self.webhook_secret
            )
            
            logger.info(f"📨 Processing webhook event: {event['type']}")
            
            # Handle different event types
            if event['type'] == 'customer.subscription.created':
                await self.handle_subscription_created(event['data']['object'])
            
            elif event['type'] == 'customer.subscription.updated':
                await self.handle_subscription_updated(event['data']['object'])
            
            elif event['type'] == 'customer.subscription.deleted':
                await self.handle_subscription_deleted(event['data']['object'])
            
            elif event['type'] == 'invoice.payment_succeeded':
                await self.handle_payment_succeeded(event['data']['object'])
            
            elif event['type'] == 'invoice.payment_failed':
                await self.handle_payment_failed(event['data']['object'])
            
            return {'success': True, 'event_type': event['type']}
            
        except stripe.error.SignatureVerificationError:
            logger.error("❌ Invalid webhook signature")
            return {'success': False, 'error': 'Invalid signature'}
        except Exception as e:
            logger.error(f"❌ Webhook processing failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def handle_subscription_created(self, subscription):
        """Handle new subscription"""
        customer_id = subscription['customer']
        tier = subscription['metadata'].get('tier', 'basic')
        
        # Update user in database with subscription details
        logger.info(f"✅ Subscription created for customer {customer_id} - Tier: {tier}")
        
        # Grant credits based on tier
        credits = self.pricing[SubscriptionTier(tier)]['credits']
        await self.grant_credits(customer_id, credits)
    
    async def handle_subscription_updated(self, subscription):
        """Handle subscription update"""
        customer_id = subscription['customer']
        tier = subscription['metadata'].get('tier', 'basic')
        status = subscription['status']
        
        logger.info(f"✅ Subscription updated for {customer_id} - Tier: {tier}, Status: {status}")
    
    async def handle_subscription_deleted(self, subscription):
        """Handle subscription cancellation"""
        customer_id = subscription['customer']
        logger.info(f"⚠️ Subscription cancelled for customer {customer_id}")
        
        # Downgrade to free tier
        await self.downgrade_to_free(customer_id)
    
    async def handle_payment_succeeded(self, invoice):
        """Handle successful payment"""
        customer_id = invoice['customer']
        amount = invoice['amount_paid']
        
        logger.info(f"✅ Payment succeeded for {customer_id} - Amount: ${amount/100:.2f}")
        
        # Grant monthly credits
        if invoice['subscription']:
            subscription = stripe.Subscription.retrieve(invoice['subscription'])
            tier = subscription['metadata'].get('tier', 'basic')
            credits = self.pricing[SubscriptionTier(tier)]['credits']
            await self.grant_credits(customer_id, credits)
    
    async def handle_payment_failed(self, invoice):
        """Handle failed payment"""
        customer_id = invoice['customer']
        logger.error(f"❌ Payment failed for customer {customer_id}")
        
        # Send notification about failed payment
        await self.notify_payment_failed(customer_id)
    
    async def grant_credits(self, customer_id: str, credits: int):
        """Grant credits to user"""
        # This would update the user's credits in the database
        logger.info(f"💳 Granted {credits} credits to customer {customer_id}")
    
    async def downgrade_to_free(self, customer_id: str):
        """Downgrade user to free tier"""
        # This would update the user's plan in the database
        logger.info(f"⬇️ Downgraded customer {customer_id} to free tier")
    
    async def notify_payment_failed(self, customer_id: str):
        """Send notification about failed payment"""
        # This would send an email/SMS notification
        logger.info(f"📧 Sent payment failure notification to {customer_id}")
    
    def get_checkout_session_url(self, customer_id: str, tier: SubscriptionTier) -> Optional[str]:
        """Create Stripe Checkout session"""
        if not self.initialized or tier == SubscriptionTier.FREE:
            return None
        
        tier_config = self.pricing[tier]
        price_id = tier_config.get('stripe_price_id')
        
        if not price_id:
            return None
        
        try:
            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1
                }],
                mode='subscription',
                success_url='https://your-domain.com/success?session_id={CHECKOUT_SESSION_ID}',
                cancel_url='https://your-domain.com/cancel',
                metadata={'tier': tier.value}
            )
            
            return session.url
            
        except Exception as e:
            logger.error(f"❌ Failed to create checkout session: {e}")
            return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get Stripe integration status"""
        return {
            'initialized': self.initialized,
            'products_configured': all(
                self.pricing[tier].get('stripe_price_id')
                for tier in [SubscriptionTier.BASIC, SubscriptionTier.PRO, SubscriptionTier.ELITE]
            ),
            'webhook_configured': bool(self.webhook_secret),
            'pricing_tiers': {
                tier.value: {
                    'price': f"${config['price']/100:.2f}",
                    'credits': config['credits'],
                    'configured': bool(config.get('stripe_price_id'))
                }
                for tier, config in self.pricing.items()
            }
        }

# Global instance
stripe_payments = StripePayments()

if __name__ == "__main__":
    # Test Stripe integration
    print("💳 Stripe Payment Integration Status")
    print("=" * 50)
    
    status = stripe_payments.get_status()
    print(f"Initialized: {'✅' if status['initialized'] else '❌'}")
    print(f"Products Configured: {'✅' if status['products_configured'] else '❌'}")
    print(f"Webhook Configured: {'✅' if status['webhook_configured'] else '❌'}")
    
    print("\n💰 Pricing Tiers:")
    for tier, info in status['pricing_tiers'].items():
        configured = '✅' if info['configured'] else '❌' if tier != 'free' else '➖'
        print(f"  {configured} {tier.upper()}: {info['price']} = {info['credits']} credits")
    
    if not status['initialized']:
        print("\n⚠️ Stripe not configured. Set environment variables:")
        print("  - STRIPE_SECRET_KEY")
        print("  - STRIPE_WEBHOOK_SECRET")