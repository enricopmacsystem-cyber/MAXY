-- Token EasyOne per chiamate API delegate per sessione utente

ALTER TABLE user_sessions
    ADD COLUMN IF NOT EXISTS easyone_access_token TEXT;
