import {loadFont as loadCrimsonPro, fontFamily as crimsonProFamily} from '@remotion/google-fonts/CrimsonPro';
import {loadFont as loadInter, fontFamily as interFamily} from '@remotion/google-fonts/Inter';

/**
 * Brand fonts per remotion/public/design/design.md's type table - Crimson
 * Pro for headlines, Inter for body/labels/buttons. Loaded once here rather
 * than per-component. Scene components take an optional `fontFamily` prop
 * (falling back to a generic sans-serif) so a future, differently-branded
 * job isn't forced into these - only pass these exports when rendering for
 * this brand.
 */
loadCrimsonPro();
loadInter();

export const HEADLINE_FONT = crimsonProFamily;
export const BODY_FONT = interFamily;
