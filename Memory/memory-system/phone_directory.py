#!/usr/bin/env python3
"""
Phone Directory System for Memory App
Manages contact relationships and phone numbers for cross-profile memory management
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import re

logger = logging.getLogger(__name__)

class PhoneDirectory:
    """
    Manages phone contacts and relationships for users
    Enables cross-profile memory management
    """
    
    def __init__(self, data_dir: str = "memory-system/data"):
        """Initialize the Phone Directory"""
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.directory_file = self.data_dir / "phone_directory.json"
        self.directory = self._load_directory()
        logger.info(f"📞 Phone Directory initialized with {len(self.directory)} users")
    
    def _load_directory(self) -> Dict[str, Dict]:
        """Load the phone directory from JSON file"""
        if self.directory_file.exists():
            try:
                with open(self.directory_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load directory: {e}")
                return {}
        return {}
    
    def _save_directory(self):
        """Save the phone directory to JSON file"""
        try:
            with open(self.directory_file, 'w', encoding='utf-8') as f:
                json.dump(self.directory, f, indent=2, ensure_ascii=False)
            logger.info(f"💾 Phone directory saved with {len(self.directory)} users")
        except Exception as e:
            logger.error(f"Failed to save directory: {e}")
    
    def _normalize_phone(self, phone: str) -> str:
        """
        Normalize phone number to standard format
        Handles international formats (+40, 0040, 07 prefixes)
        """
        # Remove all non-digit characters except +
        phone = re.sub(r'[^\d+]', '', phone)
        
        # Handle Romanian phone numbers specifically
        if phone.startswith('0040'):
            phone = '+40' + phone[4:]
        elif phone.startswith('40') and len(phone) > 10:
            phone = '+40' + phone[2:]
        elif phone.startswith('07') and len(phone) == 10:
            phone = '+407' + phone[2:]
        elif not phone.startswith('+'):
            # If no country code, assume Romanian
            if phone.startswith('0'):
                phone = '+40' + phone[1:]
            else:
                phone = '+' + phone
        
        return phone
    
    def register_contact(self, user_phone: str, contact_name: str, 
                        contact_phone: str, relationship: str = "contact") -> Dict[str, Any]:
        """
        Register a contact for a user
        
        Args:
            user_phone: The user's phone number
            contact_name: Name of the contact
            contact_phone: Phone number of the contact
            relationship: Relationship type (wife, mother, friend, etc.)
        
        Returns:
            Dict with success status and message
        """
        user_phone = self._normalize_phone(user_phone)
        contact_phone = self._normalize_phone(contact_phone)
        
        # Initialize user if not exists
        if user_phone not in self.directory:
            self.directory[user_phone] = {
                'registered_at': datetime.now().isoformat(),
                'contacts': {}
            }
        
        # Add or update contact
        self.directory[user_phone]['contacts'][contact_name.lower()] = {
            'name': contact_name,
            'phone': contact_phone,
            'relationship': relationship,
            'added_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat()
        }
        
        self._save_directory()
        
        logger.info(f"✅ Registered contact {contact_name} ({relationship}) for user {user_phone}")
        return {
            'success': True,
            'message': f"Contact {contact_name} registered as {relationship}",
            'contact_phone': contact_phone
        }
    
    def find_phone_by_name(self, user_phone: str, contact_name: str) -> Optional[str]:
        """
        Find a contact's phone number by their name
        
        Args:
            user_phone: The user's phone number
            contact_name: Name of the contact to find
        
        Returns:
            Phone number if found, None otherwise
        """
        user_phone = self._normalize_phone(user_phone)
        contact_name_lower = contact_name.lower()
        
        if user_phone in self.directory:
            contacts = self.directory[user_phone].get('contacts', {})
            
            # Exact match
            if contact_name_lower in contacts:
                return contacts[contact_name_lower]['phone']
            
            # Partial match
            for name, contact in contacts.items():
                if contact_name_lower in name or name in contact_name_lower:
                    return contact['phone']
            
            # Check by relationship
            for contact in contacts.values():
                if contact['relationship'].lower() == contact_name_lower:
                    return contact['phone']
        
        return None
    
    def get_all_contacts(self, user_phone: str) -> List[Dict[str, Any]]:
        """
        Get all contacts for a user
        
        Args:
            user_phone: The user's phone number
        
        Returns:
            List of contact dictionaries
        """
        user_phone = self._normalize_phone(user_phone)
        
        if user_phone in self.directory:
            contacts = self.directory[user_phone].get('contacts', {})
            return [
                {
                    'name': contact['name'],
                    'phone': contact['phone'],
                    'relationship': contact['relationship'],
                    'added_at': contact.get('added_at', 'Unknown')
                }
                for contact in contacts.values()
            ]
        
        return []
    
    def update_contact(self, user_phone: str, contact_name: str, 
                      new_phone: Optional[str] = None, 
                      new_relationship: Optional[str] = None) -> Dict[str, Any]:
        """
        Update a contact's information
        
        Args:
            user_phone: The user's phone number
            contact_name: Name of the contact to update
            new_phone: New phone number (optional)
            new_relationship: New relationship (optional)
        
        Returns:
            Dict with success status and message
        """
        user_phone = self._normalize_phone(user_phone)
        contact_name_lower = contact_name.lower()
        
        if user_phone not in self.directory:
            return {
                'success': False,
                'message': f"User {user_phone} not found in directory"
            }
        
        contacts = self.directory[user_phone].get('contacts', {})
        
        if contact_name_lower not in contacts:
            return {
                'success': False,
                'message': f"Contact {contact_name} not found"
            }
        
        # Update contact
        if new_phone:
            contacts[contact_name_lower]['phone'] = self._normalize_phone(new_phone)
        if new_relationship:
            contacts[contact_name_lower]['relationship'] = new_relationship
        
        contacts[contact_name_lower]['last_updated'] = datetime.now().isoformat()
        
        self._save_directory()
        
        logger.info(f"📝 Updated contact {contact_name} for user {user_phone}")
        return {
            'success': True,
            'message': f"Contact {contact_name} updated successfully"
        }
    
    def delete_contact(self, user_phone: str, contact_name: str) -> Dict[str, Any]:
        """
        Delete a contact from user's directory
        
        Args:
            user_phone: The user's phone number
            contact_name: Name of the contact to delete
        
        Returns:
            Dict with success status and message
        """
        user_phone = self._normalize_phone(user_phone)
        contact_name_lower = contact_name.lower()
        
        if user_phone not in self.directory:
            return {
                'success': False,
                'message': f"User {user_phone} not found in directory"
            }
        
        contacts = self.directory[user_phone].get('contacts', {})
        
        if contact_name_lower not in contacts:
            return {
                'success': False,
                'message': f"Contact {contact_name} not found"
            }
        
        del contacts[contact_name_lower]
        self._save_directory()
        
        logger.info(f"🗑️ Deleted contact {contact_name} for user {user_phone}")
        return {
            'success': True,
            'message': f"Contact {contact_name} deleted successfully"
        }
    
    def find_contacts_by_relationship(self, user_phone: str, relationship: str) -> List[Dict[str, Any]]:
        """
        Find all contacts with a specific relationship
        
        Args:
            user_phone: The user's phone number
            relationship: Relationship type to search for
        
        Returns:
            List of matching contacts
        """
        user_phone = self._normalize_phone(user_phone)
        
        if user_phone not in self.directory:
            return []
        
        contacts = self.directory[user_phone].get('contacts', {})
        matching = []
        
        for contact in contacts.values():
            if contact['relationship'].lower() == relationship.lower():
                matching.append({
                    'name': contact['name'],
                    'phone': contact['phone'],
                    'relationship': contact['relationship']
                })
        
        return matching
    
    def get_reverse_lookup(self, contact_phone: str) -> List[Dict[str, Any]]:
        """
        Find all users who have this phone number as a contact
        
        Args:
            contact_phone: Phone number to look up
        
        Returns:
            List of users who have this contact
        """
        contact_phone = self._normalize_phone(contact_phone)
        results = []
        
        for user_phone, user_data in self.directory.items():
            contacts = user_data.get('contacts', {})
            for contact in contacts.values():
                if contact['phone'] == contact_phone:
                    results.append({
                        'user_phone': user_phone,
                        'contact_name': contact['name'],
                        'relationship': contact['relationship']
                    })
        
        return results
    
    def export_directory(self) -> Dict[str, Any]:
        """Export the entire directory for backup purposes"""
        return {
            'exported_at': datetime.now().isoformat(),
            'total_users': len(self.directory),
            'directory': self.directory
        }
    
    def import_directory(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Import a directory backup"""
        try:
            if 'directory' in data:
                self.directory = data['directory']
                self._save_directory()
                return {
                    'success': True,
                    'message': f"Imported {len(self.directory)} users"
                }
            else:
                return {
                    'success': False,
                    'message': "Invalid import data format"
                }
        except Exception as e:
            return {
                'success': False,
                'message': f"Import failed: {str(e)}"
            }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the phone directory"""
        total_users = len(self.directory)
        total_contacts = sum(len(user_data.get('contacts', {})) 
                           for user_data in self.directory.values())
        
        relationship_counts = {}
        for user_data in self.directory.values():
            for contact in user_data.get('contacts', {}).values():
                rel = contact['relationship']
                relationship_counts[rel] = relationship_counts.get(rel, 0) + 1
        
        return {
            'total_users': total_users,
            'total_contacts': total_contacts,
            'average_contacts_per_user': total_contacts / total_users if total_users > 0 else 0,
            'relationship_breakdown': relationship_counts
        }

# Global instance
phone_directory = PhoneDirectory()

# Example usage and test data initialization
def initialize_test_data():
    """Initialize test data for the phone directory"""
    # Test data as specified
    phone_directory.register_contact(
        user_phone="40744602272",
        contact_name="Elena",
        contact_phone="40744123456",
        relationship="wife"
    )
    
    phone_directory.register_contact(
        user_phone="40744602272",
        contact_name="Maria",
        contact_phone="40744789012",
        relationship="mother"
    )
    
    logger.info("📱 Test data initialized in phone directory")

if __name__ == "__main__":
    # Initialize test data when run directly
    logging.basicConfig(level=logging.INFO)
    initialize_test_data()
    
    # Display statistics
    stats = phone_directory.get_statistics()
    print(f"\n📊 Phone Directory Statistics:")
    print(f"   Total Users: {stats['total_users']}")
    print(f"   Total Contacts: {stats['total_contacts']}")
    print(f"   Relationships: {stats['relationship_breakdown']}")