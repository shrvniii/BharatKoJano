from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.conf import settings
from .models import AnswerKey
from .views import is_module_locked, is_key_locked

class AnswerKeyLockTests(TestCase):
    def setUp(self):
        # Create user and log in
        self.user = User.objects.create_user(username='admin', password='password123')
        self.client = Client()
        self.client.login(username='admin', password='password123')
        
        # Test configurations
        self.answers = [1] * 50

    def test_module_lock_status(self):
        # Initial state: no keys in database
        self.assertFalse(is_module_locked())
        
        # Create 3 keys
        AnswerKey.objects.create(group='JUNIOR', paper_set='SET_A', answers=self.answers)
        AnswerKey.objects.create(group='JUNIOR', paper_set='SET_B', answers=self.answers)
        AnswerKey.objects.create(group='SENIOR', paper_set='SET_A', answers=self.answers)
        
        # Still not locked (only 3 keys)
        self.assertFalse(is_module_locked())
        
        # Create 4th key
        fourth_key = AnswerKey.objects.create(group='SENIOR', paper_set='SET_B', answers=self.answers)
        
        # Now it must be locked
        self.assertTrue(is_module_locked())
        self.assertTrue(is_key_locked(fourth_key))

    def test_unlock_endpoint(self):
        # Correct password
        response = self.client.post(
            reverse('answer_keys:unlock'),
            data={'password': 'bkj_qms_2026'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        self.assertTrue(self.client.session.get('answer_keys_unlocked'))
        
        # Clear session
        session = self.client.session
        del session['answer_keys_unlocked']
        session.save()
        
        # Incorrect password
        response = self.client.post(
            reverse('answer_keys:unlock'),
            data={'password': 'wrong_password'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['success'])
        self.assertIsNone(self.client.session.get('answer_keys_unlocked'))

    def test_configure_page_disabled_when_locked(self):
        # Create all 4 keys to lock the module
        AnswerKey.objects.create(group='JUNIOR', paper_set='SET_A', answers=self.answers)
        AnswerKey.objects.create(group='JUNIOR', paper_set='SET_B', answers=self.answers)
        AnswerKey.objects.create(group='SENIOR', paper_set='SET_A', answers=self.answers)
        key = AnswerKey.objects.create(group='SENIOR', paper_set='SET_B', answers=self.answers)
        
        # Access configure GET when locked and not authenticated
        response = self.client.get(reverse('answer_keys:configure', kwargs={'group': 'SENIOR', 'paper_set': 'SET_B'}))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_locked'])
        self.assertFalse(response.context['session_unlocked'])
        # Form field should be disabled
        self.assertTrue(response.context['form'].fields['q_1'].disabled)
        
        # Post request should be rejected
        post_data = {f'q_{i}': 2 for i in range(1, 51)}
        response = self.client.post(
            reverse('answer_keys:configure', kwargs={'group': 'SENIOR', 'paper_set': 'SET_B'}),
            data=post_data
        )
        # Should redirect with warning message
        self.assertRedirects(response, reverse('answer_keys:status'))
        # Key answers should remain unchanged
        key.refresh_from_db()
        self.assertEqual(key.answers[0], 1)

    def test_configure_page_enabled_when_unlocked(self):
        # Create all 4 keys to lock the module
        AnswerKey.objects.create(group='JUNIOR', paper_set='SET_A', answers=self.answers)
        AnswerKey.objects.create(group='JUNIOR', paper_set='SET_B', answers=self.answers)
        AnswerKey.objects.create(group='SENIOR', paper_set='SET_A', answers=self.answers)
        key = AnswerKey.objects.create(group='SENIOR', paper_set='SET_B', answers=self.answers)
        
        # Unlock via session
        session = self.client.session
        session['answer_keys_unlocked'] = True
        session.save()
        
        # Access configure GET when locked and authenticated
        response = self.client.get(reverse('answer_keys:configure', kwargs={'group': 'SENIOR', 'paper_set': 'SET_B'}))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_locked'])
        self.assertTrue(response.context['session_unlocked'])
        # Form field should not be disabled
        self.assertFalse(response.context['form'].fields['q_1'].disabled)
        
        # Save modifications
        post_data = {f'q_{i}': 2 for i in range(1, 51)}
        response = self.client.post(
            reverse('answer_keys:configure', kwargs={'group': 'SENIOR', 'paper_set': 'SET_B'}),
            data=post_data
        )
        self.assertRedirects(response, reverse('answer_keys:status'))
        
        # Verify edits saved
        key.refresh_from_db()
        self.assertEqual(key.answers[0], 2)
        # Verify automatic re-lock
        self.assertIsNone(self.client.session.get('answer_keys_unlocked'))

    def test_exit_page_clears_unlock_session(self):
        # Unlock via session
        session = self.client.session
        session['answer_keys_unlocked'] = True
        session.save()
        
        # Visit status page
        response = self.client.get(reverse('answer_keys:status'))
        self.assertEqual(response.status_code, 200)
        
        # Session unlock should be deleted
        self.assertIsNone(self.client.session.get('answer_keys_unlocked'))
