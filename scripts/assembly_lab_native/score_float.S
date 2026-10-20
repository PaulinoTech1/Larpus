/* Same four-accumulator reduction as deployed half kernel; lossless fp32 input.
 * SysV ABI: rdi=matrix,rsi=query,rdx=out,rcx=rows,r8=dimensions. */
.intel_syntax noprefix
.text
.global larpus_score_float
.type larpus_score_float,@function
larpus_score_float:
 test rcx,rcx
 jz .Lf_success
 test rdi,rdi
 jz .Lf_invalid
 test rsi,rsi
 jz .Lf_invalid
 test rdx,rdx
 jz .Lf_invalid
 test r8,r8
 jz .Lf_invalid
.Lf_row:
 vxorps ymm0,ymm0,ymm0
 vxorps ymm1,ymm1,ymm1
 vxorps ymm2,ymm2,ymm2
 vxorps ymm3,ymm3,ymm3
 xor rax,rax
 mov r9,r8
 and r9,-32
 test r9,r9
 jz .Lf_reduce
.Lf_block:
 vmovups ymm4,ymmword ptr [rdi+rax*4]
 vfmadd231ps ymm0,ymm4,ymmword ptr [rsi+rax*4]
 vmovups ymm4,ymmword ptr [rdi+rax*4+32]
 vfmadd231ps ymm1,ymm4,ymmword ptr [rsi+rax*4+32]
 vmovups ymm4,ymmword ptr [rdi+rax*4+64]
 vfmadd231ps ymm2,ymm4,ymmword ptr [rsi+rax*4+64]
 vmovups ymm4,ymmword ptr [rdi+rax*4+96]
 vfmadd231ps ymm3,ymm4,ymmword ptr [rsi+rax*4+96]
 add rax,32
 cmp rax,r9
 jb .Lf_block
.Lf_reduce:
 vaddps ymm0,ymm0,ymm1
 vaddps ymm2,ymm2,ymm3
 vaddps ymm0,ymm0,ymm2
 vextractf128 xmm1,ymm0,1
 vaddps xmm0,xmm0,xmm1
 vhaddps xmm0,xmm0,xmm0
 vhaddps xmm0,xmm0,xmm0
 cmp rax,r8
 jae .Lf_store
.Lf_tail:
 vmovss xmm4,dword ptr [rdi+rax*4]
 vmulss xmm4,xmm4,dword ptr [rsi+rax*4]
 vaddss xmm0,xmm0,xmm4
 inc rax
 cmp rax,r8
 jb .Lf_tail
.Lf_store:
 vmovss dword ptr [rdx],xmm0
 lea rdi,[rdi+r8*4]
 add rdx,4
 dec rcx
 jnz .Lf_row
.Lf_success:
 vzeroupper
 xor eax,eax
 ret
.Lf_invalid:
 mov eax,-1
 ret
.size larpus_score_float,.-larpus_score_float
.section .note.GNU-stack,"",@progbits
