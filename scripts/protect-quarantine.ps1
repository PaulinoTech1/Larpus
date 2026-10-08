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
$actual = Get-Acl -LiteralPath $Target
if (!$actual.AreAccessRulesProtected) { throw 'ACL inheritance remains enabled' }
foreach ($rule in $actual.Access) {
    $sid = $rule.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value
    if ($sid -notin @($owner.Value, $system.Value)) { throw 'Unexpected quarantine principal' }
}
