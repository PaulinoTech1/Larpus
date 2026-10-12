param([Parameter(Mandatory=$true)][string]$Target)
$ErrorActionPreference = 'Stop'
$item = Get-Item -LiteralPath $Target
if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Reparse point rejected' }
$owner = [Security.Principal.WindowsIdentity]::GetCurrent().User
$system = [Security.Principal.SecurityIdentifier]::new('S-1-5-18')
$acl = $item.GetAccessControl([Security.AccessControl.AccessControlSections]::Access)
$acl.SetAccessRuleProtection($true, $false)
foreach ($existing in @($acl.Access)) { $acl.RemoveAccessRuleSpecific($existing) }
foreach ($sid in @($owner, $system)) {
    $rule = [Security.AccessControl.FileSystemAccessRule]::new($sid, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow')
    $acl.AddAccessRule($rule)
}
$item.SetAccessControl($acl)
# Verify via .NET only: the Microsoft.PowerShell.Security module behind Get-Acl is not
# reliably loadable in Windows PowerShell 5.1 on all hosts, so avoid the cmdlet here.
$verify = (Get-Item -LiteralPath $Target).GetAccessControl([Security.AccessControl.AccessControlSections]::Access)
if (!$verify.AreAccessRulesProtected) { throw 'ACL inheritance remains enabled' }
foreach ($rule in $verify.GetAccessRules($true, $false, [Security.Principal.SecurityIdentifier])) {
    if ($rule.IdentityReference.Value -notin @($owner.Value, $system.Value)) { throw 'Unexpected quarantine principal' }
}
