/*
   Copyright 2025 Kyant

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
 */

package glassify.kyant;

// Adapted for Android View RenderNodes. Upstream AndroidLiquidGlass eb4a0ea (Apache-2.0).
final class Refraction {
    static final String AGSL = """
        uniform shader content;

        uniform float2 size;
        uniform float2 offset;
        uniform float4 cornerRadii;
        uniform float refractionHeight;
        uniform float outerEdgeBand;
        uniform float refractionAmount;
        uniform float depthEffect;
        uniform float chromaticAberration;

        float radiusAt(float2 centeredCoord, float4 radii) {
            if (centeredCoord.x >= 0.0) {
                if (centeredCoord.y <= 0.0) return radii.y;
                else return radii.z;
            } else {
                if (centeredCoord.y <= 0.0) return radii.x;
                else return radii.w;
            }
        }

        float sdRoundedRect(float2 coord, float2 halfSize, float radius) {
            float2 cornerCoord = abs(coord) - (halfSize - float2(radius));
            float outside = length(max(cornerCoord, 0.0)) - radius;
            float inside = min(max(cornerCoord.x, cornerCoord.y), 0.0);
            return outside + inside;
        }

        float2 gradSdRoundedRect(float2 coord, float2 halfSize, float radius) {
            float2 cornerCoord = abs(coord) - (halfSize - float2(radius));
            if (cornerCoord.x >= 0.0 || cornerCoord.y >= 0.0) {
                return sign(coord) * (max(cornerCoord, 0.0) / max(length(max(cornerCoord, 0.0)), 0.0001));
            } else {
                float gradX = step(cornerCoord.y, cornerCoord.x);
                return sign(coord) * float2(gradX, 1.0 - gradX);
            }
        }

        // Cubic displacement curve from Telegram iOS LegacyGlassView, evaluated only on the rim.
        float displacement(float x) {
            float t = x;
            for (int i = 0; i < 4; i++) {
                float atT = ((1.7063492 * t - 3.1547619) * t + 2.4484127) * t;
                float slope = (5.1190476 * t - 6.3095238) * t + 2.4484127;
                t = clamp(t - (atT - x) / slope, 0.0, 1.0);
            }
            return ((-1.0039683 * t + 1.3888889) * t + 0.6150794) * t;
        }

        half4 sampleInside(float2 coord) {
            return content.eval(clamp(coord, -offset, size - offset));
        }

        half4 main(float2 coord) {
            float2 halfSize = size * 0.5;
            float2 centeredCoord = (coord + offset) - halfSize;
            float radius = radiusAt(centeredCoord, cornerRadii);

            float sd = sdRoundedRect(centeredCoord, halfSize, radius);
            if (sd > 0.0 || -sd >= refractionHeight) {
                return content.eval(coord);
            }

            float boost = 1.0 + 0.5 * smoothstep(0.0, outerEdgeBand, outerEdgeBand + sd);
            float d = displacement(1.0 + sd / refractionHeight) * boost * refractionAmount;
            float2 n = gradSdRoundedRect(centeredCoord, halfSize, radius) + depthEffect * centeredCoord / max(length(centeredCoord), 0.0001);
            float2 grad = n / max(length(n), 0.0001);

            float2 refractedCoord = coord + d * grad;
            if (chromaticAberration <= 0.0) return sampleInside(refractedCoord);
            float dispersionIntensity = chromaticAberration * ((centeredCoord.x * centeredCoord.y) / (halfSize.x * halfSize.y));
            float2 dispersedCoord = d * grad * dispersionIntensity;

            half4 color = half4(0.0);

            half4 red = sampleInside(refractedCoord + dispersedCoord);
            color.r += red.r / 3.5;
            color.a += red.a / 7.0;

            half4 orange = sampleInside(refractedCoord + dispersedCoord * (2.0 / 3.0));
            color.r += orange.r / 3.5;
            color.g += orange.g / 7.0;
            color.a += orange.a / 7.0;

            half4 yellow = sampleInside(refractedCoord + dispersedCoord * (1.0 / 3.0));
            color.r += yellow.r / 3.5;
            color.g += yellow.g / 3.5;
            color.a += yellow.a / 7.0;

            half4 green = sampleInside(refractedCoord);
            color.g += green.g / 3.5;
            color.a += green.a / 7.0;

            half4 cyan = sampleInside(refractedCoord - dispersedCoord * (1.0 / 3.0));
            color.g += cyan.g / 3.5;
            color.b += cyan.b / 3.0;
            color.a += cyan.a / 7.0;

            half4 blue = sampleInside(refractedCoord - dispersedCoord * (2.0 / 3.0));
            color.b += blue.b / 3.0;
            color.a += blue.a / 7.0;

            half4 purple = sampleInside(refractedCoord - dispersedCoord);
            color.r += purple.r / 7.0;
            color.b += purple.b / 3.0;
            color.a += purple.a / 7.0;

            return color;
        }
        """;
    static final String HIGHLIGHT = """
        uniform float2 origin;
        uniform float2 size;
        uniform float4 cornerRadii;
        layout(color) uniform half4 color;
        uniform float angle;
        uniform float falloff;

        float radiusAt(float2 centeredCoord, float4 radii) {
            if (centeredCoord.x >= 0.0) {
                if (centeredCoord.y <= 0.0) return radii.y;
                else return radii.z;
            } else {
                if (centeredCoord.y <= 0.0) return radii.x;
                else return radii.w;
            }
        }

        float sdRoundedRect(float2 coord, float2 halfSize, float radius) {
            float2 cornerCoord = abs(coord) - (halfSize - float2(radius));
            float outside = length(max(cornerCoord, 0.0)) - radius;
            float inside = min(max(cornerCoord.x, cornerCoord.y), 0.0);
            return outside + inside;
        }

        float2 gradSdRoundedRect(float2 coord, float2 halfSize, float radius) {
            float2 cornerCoord = abs(coord) - (halfSize - float2(radius));
            if (cornerCoord.x >= 0.0 || cornerCoord.y >= 0.0) {
                return sign(coord) * (max(cornerCoord, 0.0) / max(length(max(cornerCoord, 0.0)), 0.0001));
            } else {
                float gradX = step(cornerCoord.y, cornerCoord.x);
                return sign(coord) * float2(gradX, 1.0 - gradX);
            }
        }

        half4 main(float2 coord) {
            float2 halfSize = size * 0.5;
            float2 centeredCoord = coord - origin - halfSize;
            float radius = radiusAt(centeredCoord, cornerRadii);

            float gradRadius = min(radius * 1.5, min(halfSize.x, halfSize.y));
            float2 grad = gradSdRoundedRect(centeredCoord, halfSize, gradRadius);
            float2 normal = float2(cos(angle), sin(angle));
            float d = dot(grad, normal);
            float intensity = pow(abs(d), falloff);
            return color * intensity;
        }
        """;
}
