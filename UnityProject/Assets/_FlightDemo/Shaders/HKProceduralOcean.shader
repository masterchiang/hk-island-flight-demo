Shader "HKFlight/ProceduralOcean"
{
    Properties
    {
        _DeepColor ("Deep Water", Color) = (0.008, 0.12, 0.19, 0.96)
        _ShallowColor ("Coastal Water", Color) = (0.035, 0.32, 0.42, 0.96)
        _SpecularColor ("Sun Glint", Color) = (0.82, 0.94, 1.0, 1)
        _Opacity ("Opacity", Range(0.8, 1)) = 0.96
        _WaveAmplitude ("Wave Height", Range(0, 1)) = 0.45
        _WaveFrequency ("Wave Frequency", Range(0.002, 0.04)) = 0.012
        _WaveSpeed ("Wave Speed", Range(0, 3)) = 0.8
        _Smoothness ("Specular Smoothness", Range(0, 1)) = 0.97
    }
    SubShader
    {
        Tags { "RenderPipeline"="UniversalPipeline" "Queue"="Transparent" "RenderType"="Transparent" }
        Pass
        {
            Name "ForwardOcean"
            Tags { "LightMode"="UniversalForward" }
            Blend SrcAlpha OneMinusSrcAlpha
            ZWrite Off
            Cull Off
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma target 3.0
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            CBUFFER_START(UnityPerMaterial)
                float4 _DeepColor;
                float4 _ShallowColor;
                float4 _SpecularColor;
                float _Opacity;
                float _WaveAmplitude;
                float _WaveFrequency;
                float _WaveSpeed;
                float _Smoothness;
            CBUFFER_END

            struct Attributes { float4 positionOS : POSITION; };
            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float3 positionWS : TEXCOORD0;
                float3 normalWS : TEXCOORD1;
            };

            Varyings Vert(Attributes input)
            {
                Varyings output;
                float3 p = TransformObjectToWorld(input.positionOS.xyz);
                float f = _WaveFrequency;
                float t = _Time.y * _WaveSpeed;
                float phaseA = dot(p.xz, float2(0.83, 0.55)) * f + t;
                float phaseB = dot(p.xz, float2(-0.42, 0.91)) * f * 1.73 - t * 0.71;
                float phaseC = dot(p.xz, float2(0.21, -0.98)) * f * 2.31 + t * 0.43;
                float amp = _WaveAmplitude;
                float height = amp * (0.55 * sin(phaseA) + 0.30 * sin(phaseB) + 0.15 * sin(phaseC));
                float dhdx = amp * (0.55 * cos(phaseA) * 0.83 * f + 0.30 * cos(phaseB) * -0.42 * f * 1.73 + 0.15 * cos(phaseC) * 0.21 * f * 2.31);
                float dhdz = amp * (0.55 * cos(phaseA) * 0.55 * f + 0.30 * cos(phaseB) * 0.91 * f * 1.73 + 0.15 * cos(phaseC) * -0.98 * f * 2.31);
                p.y += height;
                output.positionWS = p;
                output.normalWS = normalize(float3(-dhdx, 1.0, -dhdz));
                output.positionCS = TransformWorldToHClip(p);
                return output;
            }

            half4 Frag(Varyings input) : SV_Target
            {
                float3 n = normalize(input.normalWS);
                float3 viewDir = SafeNormalize(_WorldSpaceCameraPos.xyz - input.positionWS);
                Light mainLight = GetMainLight();
                float ndl = saturate(dot(n, mainLight.direction));
                float3 halfDir = SafeNormalize(mainLight.direction + viewDir);
                float spec = pow(saturate(dot(n, halfDir)), lerp(36.0, 192.0, _Smoothness)) * ndl;
                float fresnel = pow(1.0 - saturate(dot(n, viewDir)), 4.0);
                float ripple = sin((input.positionWS.x + input.positionWS.z * 0.42) * 0.018 + _Time.y * 0.75)
                             * sin((input.positionWS.z - input.positionWS.x * 0.31) * 0.026 - _Time.y * 0.52);
                float coastalMix = saturate(0.27 + fresnel * 0.62 + ripple * 0.05);
                float3 water = lerp(_DeepColor.rgb, _ShallowColor.rgb, coastalMix);
                float3 lit = water * (0.72 + ndl * mainLight.color * 0.48);
                lit += _SpecularColor.rgb * spec * 1.9;
                lit += _ShallowColor.rgb * fresnel * 0.28;
                return half4(lit, _Opacity);
            }
            ENDHLSL
        }
    }
}
