import "server-only";

export type RateLimiterOptions = {
  capacity: number;
  refillPerMinute: number;
};

// Token bucket with a FIFO waiter queue. Callers await `acquire()` before each
// upstream request; waiters are released in arrival order as tokens refill.
export class TokenBucket {
  private tokens: number;
  private lastRefill: number;
  private readonly refillPerMs: number;
  private readonly capacity: number;
  private readonly queue: Array<() => void> = [];
  private timer: ReturnType<typeof setTimeout> | null = null;

  constructor(opts: RateLimiterOptions) {
    this.capacity = opts.capacity;
    this.tokens = opts.capacity;
    this.refillPerMs = opts.refillPerMinute / 60_000;
    this.lastRefill = Date.now();
  }

  acquire(): Promise<void> {
    return new Promise((resolve) => {
      this.queue.push(resolve);
      this.drain();
    });
  }

  snapshot() {
    this.refill();
    return {
      tokens: this.tokens,
      capacity: this.capacity,
      queued: this.queue.length,
    };
  }

  private drain() {
    this.refill();
    while (this.queue.length > 0 && this.tokens >= 1) {
      this.tokens -= 1;
      const next = this.queue.shift();
      next?.();
    }
    if (this.queue.length > 0 && this.timer === null) {
      const deficit = 1 - this.tokens;
      const waitMs = Math.max(1, Math.ceil(deficit / this.refillPerMs));
      this.timer = setTimeout(() => {
        this.timer = null;
        this.drain();
      }, waitMs);
    }
  }

  private refill() {
    const now = Date.now();
    const elapsed = now - this.lastRefill;
    if (elapsed <= 0) return;
    this.tokens = Math.min(this.capacity, this.tokens + elapsed * this.refillPerMs);
    this.lastRefill = now;
  }
}
