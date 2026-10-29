#version 440
layout(location=0) in vec2 qt_TexCoord0;
layout(location=0) out vec4 fragColor;
layout(std140,binding=0) uniform Params {
    mat4 qt_Matrix;
    float qt_Opacity;
    vec2 sourceSize;
    vec2 origin;
    float corner;
    float coating;
    float blur;
    vec2 resolution;
};
layout(binding=1) uniform sampler2D backdrop;
vec3 sampleAt(vec2 p) {
    return texture(backdrop,clamp(p/max(sourceSize,vec2(1)),vec2(.001),vec2(.999))).rgb;
}
void main() {
    vec2 px=qt_TexCoord0*resolution;
    vec2 q=abs(px-resolution*.5)-resolution*.5+corner;
    float d=length(max(q,0.0))+min(max(q.x,q.y),0.0)-corner;
    float coverage=1.0-smoothstep(-.7,.7,d);
    if(coverage<=0.0) { fragColor=vec4(0);return; }
    vec2 at=origin+px;
    vec3 scene=sampleAt(at)*.28;
    scene+=(sampleAt(at+vec2(blur,0))+sampleAt(at-vec2(blur,0))
           +sampleAt(at+vec2(0,blur))+sampleAt(at-vec2(0,blur)))*.12;
    scene+=(sampleAt(at+vec2(blur))+sampleAt(at-vec2(blur))
           +sampleAt(at+vec2(blur,-blur))+sampleAt(at+vec2(-blur,blur)))*.06;
    vec3 surface=mix(scene,vec3(.085),coating);
    surface+=vec3(exp(-abs(d+.7)*1.7)*.035);
    fragColor=vec4(surface*coverage,coverage)*qt_Opacity;
}
