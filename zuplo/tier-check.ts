import { ZuploContext, ZuploRequest, HttpProblems } from "@zuplo/runtime";

/**
 * Tier Check Policy
 * 
 * Checks if the authenticated user's subscription tier
 * meets the minimum requirement for this endpoint.
 * 
 * Tier hierarchy: community < pro < studio
 * 
 * User metadata (set when creating API key consumers in Zuplo):
 *   metadata.tier = "community" | "pro" | "studio"
 */

const TIER_LEVELS: Record<string, number> = {
  community: 0,
  free: 0,
  pro: 1,
  studio: 2,
  enterprise: 3,
};

type PolicyOptions = {
  requiredTier: string;
};

export default async function policy(
  request: ZuploRequest,
  context: ZuploContext,
  options: PolicyOptions,
  policyName: string,
) {
  const requiredLevel = TIER_LEVELS[options.requiredTier] ?? 1;

  // The user object is set by the api-key-auth policy
  const user = request.user;

  if (!user) {
    return HttpProblems.unauthorized(request, context, {
      detail: "Authentication required",
    });
  }

  // Get tier from user metadata (set on the API key consumer)
  const userTier = (user.data?.tier as string) ?? "community";
  const userLevel = TIER_LEVELS[userTier] ?? 0;

  if (userLevel < requiredLevel) {
    context.log.info(
      `Tier check failed: user=${user.sub}, tier=${userTier}, required=${options.requiredTier}`,
    );

    return HttpProblems.forbidden(request, context, {
      detail: `This endpoint requires ${options.requiredTier} tier or above. Your current tier: ${userTier}. Upgrade at https://arcwright.app/pricing`,
    });
  }

  context.log.debug(
    `Tier check passed: user=${user.sub}, tier=${userTier}, required=${options.requiredTier}`,
  );

  // Continue to next policy / handler
  return request;
}
