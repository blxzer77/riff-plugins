export interface LimiterConfig {
  windowMs: number;
  max: number;
}

export function limiterConfig(): LimiterConfig {
  return {
    windowMs: process.env.RATE_LIMIT_WINDOW_MS as any,
    max: process.env.RATE_LIMIT_MAX as any,
  };
}
