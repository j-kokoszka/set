import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';

interface FeedbackButtonProps {
  getValidToken: () => Promise<string | null>;
}

const FeedbackButton: React.FC<FeedbackButtonProps> = ({ getValidToken }) => {
  const { t } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const [message, setMessage] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim()) return;

    setIsSubmitting(true);
    setError(null);

    try {
      const token = await getValidToken();
      if (!token) {
        throw new Error(t('feedback.error_no_token', 'You must be logged in to send feedback.'));
      }

      const response = await fetch('/api/feedback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ text: message })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || t('feedback.error_generic', 'Failed to submit feedback'));
      }

      alert(t('feedback.success', 'Feedback submitted successfully'));
      setMessage('');
      setIsOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('common.unknown_error', 'An unknown error occurred'));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      <button 
        className="fab" 
        onClick={() => setIsOpen(true)}
        aria-label={t('feedback.button_title', 'Send Feedback')}
      >
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
        </svg>
      </button>

      {isOpen && (
        <div className="modal-overlay" onClick={() => setIsOpen(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2 className="modal-title">{t('feedback.button_title', 'Send Feedback / Report Bug')}</h2>
            <form onSubmit={handleSubmit}>
              <textarea
                className="feedback-textarea"
                placeholder={t('feedback.placeholder', 'Describe the issue or suggest an improvement...')}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                disabled={isSubmitting}
                required
              />
              {error && <p style={{ color: '#ef4444', marginBottom: '1rem' }}>{error}</p>}
              <div className="modal-actions">
                <button 
                  type="button" 
                  className="btn btn-secondary" 
                  onClick={() => setIsOpen(false)}
                  disabled={isSubmitting}
                >
                  {t('common.cancel', 'Cancel')}
                </button>
                <button 
                  type="submit" 
                  className="btn" 
                  disabled={isSubmitting || !message.trim()}
                >
                  {isSubmitting ? t('feedback.sending', 'Sending...') : t('feedback.submit', 'Submit')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
};

export default FeedbackButton;
