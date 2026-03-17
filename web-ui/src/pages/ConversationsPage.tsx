import { useEffect, useState } from 'react';
import type { ChannelInfo, HistoryMessage } from '../types/api';
import { getChannels, getHistory, deleteMessage, clearChannel } from '../api/client';
import { TimeAgo } from '../components/TimeAgo';

export function ConversationsPage() {
  const [channels, setChannels] = useState<ChannelInfo[]>([]);
  const [selectedChannel, setSelectedChannel] = useState<string | null>(null);
  const [messages, setMessages] = useState<HistoryMessage[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getChannels().then(setChannels);
  }, []);

  async function selectChannel(channel: string) {
    setSelectedChannel(channel);
    setLoading(true);
    try {
      const history = await getHistory(channel, 50);
      setMessages([...history].reverse()); // oldest first
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(id: number) {
    if (!selectedChannel) return;
    await deleteMessage(selectedChannel, id);
    setMessages((prev) => prev.filter((m) => m.id !== id));
  }

  async function handleClear() {
    if (!selectedChannel) return;
    if (!confirm(`Clear all messages in "${selectedChannel}"?`)) return;
    await clearChannel(selectedChannel);
    setMessages([]);
    const updated = await getChannels();
    setChannels(updated);
  }

  return (
    <div className="flex gap-4 min-h-[500px]">
      {/* Sidebar */}
      <div className="w-56 flex-shrink-0 bg-bg-secondary border border-border-primary rounded-lg overflow-hidden">
        <div className="p-3 border-b border-border-primary">
          <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wide">Channels</h3>
        </div>
        <div className="overflow-y-auto max-h-[500px]">
          {channels.map((ch) => (
            <div
              key={ch.channel}
              onClick={() => selectChannel(ch.channel)}
              className={`px-3 py-2.5 cursor-pointer border-b border-border-secondary hover:bg-bg-tertiary ${
                selectedChannel === ch.channel ? 'bg-bg-tertiary' : ''
              }`}
            >
              <div className="text-sm text-text-secondary">{ch.channel}</div>
              <div className="text-xs text-text-muted">
                {ch.message_count} messages &middot; <TimeAgo timestamp={ch.last_active} />
              </div>
            </div>
          ))}
          {channels.length === 0 && (
            <div className="px-3 py-4 text-sm text-text-muted">No channels</div>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 bg-bg-secondary border border-border-primary rounded-lg overflow-hidden">
        {!selectedChannel ? (
          <div className="flex items-center justify-center h-full text-text-muted text-sm">
            Select a channel to view messages
          </div>
        ) : loading ? (
          <div className="flex items-center justify-center h-full text-text-muted text-sm">
            Loading...
          </div>
        ) : (
          <div className="flex flex-col h-full">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-border-primary">
              <h3 className="text-sm font-semibold text-text-primary">{selectedChannel}</h3>
              {messages.length > 0 && (
                <button
                  onClick={handleClear}
                  className="text-xs text-danger hover:text-danger-hover cursor-pointer"
                >
                  Clear All
                </button>
              )}
            </div>

            {/* Message list */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 max-h-[500px]">
              {messages.length === 0 ? (
                <p className="text-text-muted text-sm">No messages</p>
              ) : (
                messages.map((msg) => (
                  <div key={msg.id} className="border-b border-border-secondary pb-4 last:border-0">
                    <div className="text-sm text-text-primary mb-1">
                      <span className="text-text-muted text-xs mr-2">User:</span>
                      {msg.message}
                    </div>
                    {msg.response && (
                      <div className="text-sm text-text-secondary mt-1 whitespace-pre-wrap">
                        <span className="text-text-muted text-xs mr-2">Assistant:</span>
                        {msg.response}
                      </div>
                    )}
                    <div className="flex justify-between items-center mt-2">
                      <span className="text-xs text-text-muted">
                        <TimeAgo timestamp={msg.timestamp} />
                        {msg.model_used && <span className="ml-2">{msg.model_used}</span>}
                        {msg.tokens_used && <span className="ml-2">{msg.tokens_used} tokens</span>}
                      </span>
                      <button
                        onClick={() => handleDelete(msg.id)}
                        className="text-xs text-danger hover:text-danger-hover cursor-pointer"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
