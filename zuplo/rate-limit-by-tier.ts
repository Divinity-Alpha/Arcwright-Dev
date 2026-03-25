import { ZuploContext, ZuploRequest } from "@zuplo/runtime";

/**
 * Rate Limit by Tier
 * 
 * Returns a different rate limit configuration based on
 * the user's subscription tier. This is used by the
 * rate-limit-generate policy.
 * 
 * Tier limits (per minute):
 *   community: 2 req/min
 *   pro:       10 req/min  
 *   studio:    20 req/min
 * 
 * Monthly caps are tracked separately via usage monitoring.
 */

type RateLimitConfig = {
  key: string;
  requestsAllowed: number;
  timeWindowMinutes: number;
};

const TIER_RATE_LIMITS: Record<string, { perMinute: number }> = {
  community: { perMinute: 2 },
  free: { perMinute: 2 },
  pro: { perMinute: 10 },
  studio: { perMinute: 20 },
  enterprise: { perMinute: 50 },
};

export function rateLimitByTier(
  request: ZuploRequest,
  context: ZuploContext,
): RateLimitConfig {
  const user = request.user;
  const userId = user?.sub ?? "anonymous";
  const userTier = (user?.data?.tier as string) ?? "community";

  const limits = TIER_RATE_LIMITS[userTier] ?? TIER_RATE_LIMITS.community;

  return {
    key: `generate:${userId}`,
    requestsAllowed: limits.perMinute,
    timeWindowMinutes: 1,
  };
}
