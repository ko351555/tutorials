import { useState } from 'react';

export default function CopyButton({ text, label = 'Copy', className = '' }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <button
      className={`btn-copy ${copied ? 'copied' : ''} ${className}`}
      onClick={handleCopy}
    >
      {copied ? '✓ Copied!' : `📋 ${label}`}
    </button>
  );
}
