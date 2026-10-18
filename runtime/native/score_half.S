/* SysV x86-64 ABI: rdi=half matrix,rsi=float query,rdx=output,
 * rcx=rows,r8=dimensions. No calls, stack writes or nonvolatile registers.
 * The checked Python wrapper supplies finite, disjoint, contiguous arrays.
 */
.intel_syntax noprefix
.text
.global larpus_score_half
.type larpus_score_half,@function
larpus_score_half:
 test rcx,rcx
 jz .Lsuccess
 test rdi,rdi
 jz .Linvalid
 test rsi,rsi
 jz .Linvalid
 test rdx,rdx
 jz .Linvalid
 test r8,r8
 jz .Linvalid
.Lrow:
 vxorps ymm0,ymm0,ymm0
 vxorps ymm1,ymm1,ymm1
 vxorps ymm2,ymm2,ymm2
 vxorps ymm3,ymm3,ymm3
 xor rax,rax
 mov r9,r8
 and r9,-32
 test r9,r9
 jz .Lreduce
.Lblock:
 vcvtph2ps ymm4,xmmword ptr [rdi+rax*2]
 vfmadd231ps ymm0,ymm4,ymmword ptr [rsi+rax*4]
 vcvtph2ps ymm4,xmmword ptr [rdi+rax*2+16]
 vfmadd231ps ymm1,ymm4,ymmword ptr [rsi+rax*4+32]
 vcvtph2ps ymm4,xmmword ptr [rdi+rax*2+32]
 vfmadd231ps ymm2,ymm4,ymmword ptr [rsi+rax*4+64]
 vcvtph2ps ymm4,xmmword ptr [rdi+rax*2+48]
 vfmadd231ps ymm3,ymm4,ymmword ptr [rsi+rax*4+96]
 add rax,32
 cmp rax,r9
 jb .Lblock
.Lreduce:
 vaddps ymm0,ymm0,ymm1
 vaddps ymm2,ymm2,ymm3
 vaddps ymm0,ymm0,ymm2
 vextractf128 xmm1,ymm0,1
 vaddps xmm0,xmm0,xmm1
 vhaddps xmm0,xmm0,xmm0
 vhaddps xmm0,xmm0,xmm0
 cmp rax,r8
 jae .Lstore
.Ltail:
 movzx r10d,word ptr [rdi+rax*2]
 vmovd xmm4,r10d
 vcvtph2ps xmm4,xmm4
 vmulss xmm4,xmm4,dword ptr [rsi+rax*4]
 vaddss xmm0,xmm0,xmm4
 inc rax
 cmp rax,r8
 jb .Ltail
.Lstore:
 vmovss dword ptr [rdx],xmm0
 lea rdi,[rdi+r8*2]
 add rdx,4
 dec rcx
 jnz .Lrow
.Lsuccess:
 vzeroupper
 xor eax,eax
 ret
.Linvalid:
 mov eax,-1
 ret
.size larpus_score_half,.-larpus_score_half
.section .note.GNU-stack,"",@progbits
