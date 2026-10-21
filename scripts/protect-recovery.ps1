param([Parameter(Mandatory=$true)][string]$Target,[switch]$Initialize)
$ErrorActionPreference = 'Stop'
$item = [IO.DirectoryInfo]::new($Target)
if (!$item.Exists -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'Recovery directory unavailable' }
$owner = [Security.Principal.WindowsIdentity]::GetCurrent().User
$system = [Security.Principal.SecurityIdentifier]::new('S-1-5-18')
$acl = $item.GetAccessControl([Security.AccessControl.AccessControlSections]::Access)
if ($Initialize) {
$acl.SetAccessRuleProtection($true, $false)
foreach ($rule in @($acl.Access)) { $acl.RemoveAccessRuleSpecific($rule) }
foreach ($sid in @($owner, $system)) {
    $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($sid, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow'))
}
$item.SetAccessControl($acl)
}
$verify = $item.GetAccessControl([Security.AccessControl.AccessControlSections]::Access)
if (!$verify.AreAccessRulesProtected) { throw 'Recovery ACL inheritance remains enabled' }
$rules = @($verify.GetAccessRules($true, $true, [Security.Principal.SecurityIdentifier]))
if ($rules.Count -ne 2) { throw 'Unexpected recovery ACL count' }
foreach ($rule in $rules) {
    if ($rule.IdentityReference.Value -notin @($owner.Value, $system.Value) -or $rule.AccessControlType -ne 'Allow' -or $rule.FileSystemRights -ne 'FullControl') { throw 'Unexpected recovery ACL' }
}
foreach ($name in @('state.json', 'supervisor.lock')) {
    $file = [IO.FileInfo]::new([IO.Path]::Combine($Target, $name))
    if (!$file.Exists) { continue }
    if ($file.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Recovery file redirected' }
    $fileRules = @($file.GetAccessControl().GetAccessRules($true, $true, [Security.Principal.SecurityIdentifier]))
    if ($fileRules.Count -ne 2) { throw 'Unexpected recovery file ACL count' }
    foreach ($rule in $fileRules) {
        if ($rule.IdentityReference.Value -notin @($owner.Value, $system.Value) -or $rule.AccessControlType -ne 'Allow' -or $rule.FileSystemRights -ne 'FullControl') { throw 'Unexpected recovery file ACL' }
    }
}
