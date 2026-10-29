#version 440
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform Params {
    mat4 qt_Matrix;
    float qt_Opacity;
    vec2 resolution;
    vec2 surfaceSize;
    vec2 sourceSize;
    float refraction;
    float tint;
};
layout(binding = 1) uniform sampler2D backdrop;
// Same optical model as ../desktop_glass_lab; attribution in ../jelly_button_lab/THIRD_PARTY.md.
float sdf(vec2 p) {
    vec2 q = abs(p) - surfaceSize * .5 + 28.0;
    return length(max(q,0.0)) + min(max(q.x,q.y),0.0) - 28.0;
}
vec3 sampleScene(vec2 p) {
    if (p.x < 0.0 || p.y < 0.0 || p.x >= sourceSize.x || p.y >= sourceSize.y)
        return vec3(.18);
    return texture(backdrop,clamp(p/sourceSize,vec2(.001),vec2(.999))).rgb;
}
void main() {
    vec2 pixel=qt_TexCoord0*resolution, p=pixel-surfaceSize*.5;
    float sd=sdf(p), coverage=1.0-smoothstep(-.8,.8,sd);
    if (coverage<=0.0) { fragColor=vec4(0); return; }
    vec2 g=vec2(sdf(p+vec2(.5,0))-sdf(p-vec2(.5,0)),sdf(p+vec2(0,.5))-sdf(p-vec2(0,.5)));
    vec2 outward=g/max(length(g),.0001);
    float edge=clamp(1.0+sd/18.0,0.0,.97);
    vec3 normal=normalize(vec3(outward*edge/sqrt(max(.04,1.0-edge*edge)),1));
    vec3 ray=refract(vec3(0,0,-1),normal,1.0/1.45);
    vec2 at=pixel+refraction*ray.xy/max(-ray.z,.15)*25.0;
    vec3 through=sampleScene(at)*.6;
    through+=(sampleScene(at+vec2(1,0))+sampleScene(at-vec2(1,0))
             +sampleScene(at+vec2(0,1))+sampleScene(at-vec2(0,1)))*.1;
    // Neutral coating preserves the desktop hue instead of painting it navy.
    vec3 glass=mix(through,vec3(.18),tint);
    float light=max(dot(outward,normalize(vec2(-.65,-.76))),0.0);
    glass+=vec3(pow(edge,5.0)*(.025+.14*pow(light,3.0))
           +exp(-abs(sd+.8)*1.35)*(.06+light*.28));
    fragColor=vec4(glass*coverage,coverage)*qt_Opacity;
}
