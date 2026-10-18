param([Parameter(Mandatory=$true)][string]$Target)
$ErrorActionPreference = 'Stop'
# .NET only, no cmdlets: resolving a cmdlet makes Windows PowerShell 5.1 run module discovery,
# which took 20-60 s per launch when PSModulePath is absent (the MCP child's allowlisted env).
$item = [IO.DirectoryInfo]::new($Target)
if (!$item.Exists) { throw 'Quarantine directory missing' }
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
# Verify via .NET only (no Get-Acl): see the module-discovery note above.
$verify = [IO.DirectoryInfo]::new($Target).GetAccessControl([Security.AccessControl.AccessControlSections]::Access)
if (!$verify.AreAccessRulesProtected) { throw 'ACL inheritance remains enabled' }
foreach ($rule in $verify.GetAccessRules($true, $false, [Security.Principal.SecurityIdentifier])) {
    if ($rule.IdentityReference.Value -notin @($owner.Value, $system.Value)) { throw 'Unexpected quarantine principal' }
}
