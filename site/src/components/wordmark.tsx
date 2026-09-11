export function Wordmark({ className = "" }: { className?: string }) {
return <span className={`wordmark ${className}`}><svg width="34" height="37" viewBox="0 0 34 37" fill="none" aria-hidden="true"><path d="M17 2 31 8v12c0 7-14 15-14 15S3 27 3 20V8L17 2Z" stroke="currentColor" strokeWidth="2.4" /><path d="m10 25 5-14h5l4 14M12 20h10" stroke="currentColor" strokeWidth="2.8" strokeLinejoin="round" /><path d="M17 12v4m0 5v4" stroke="currentColor" strokeWidth="1.5" /></svg><span>rota<span className="wordmark-light">guard</span></span></span>;
}
