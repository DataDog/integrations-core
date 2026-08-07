/// Minimal interoperability production used only to make the built-in
/// iris_interop_* OpenMetrics families appear on the /api/monitor/metrics
/// endpoint. It runs the EnsLib testing hosts so the check has a live
/// production to observe; no external connectivity is required.
Class Demo.MonitorProduction Extends Ens.Production
{

XData ProductionDefinition
{
<Production Name="Demo.MonitorProduction" TestingEnabled="true" LogGeneralTraceEvents="false">
  <Item Name="TestProcess" ClassName="EnsLib.Testing.Process" PoolSize="1" Enabled="true"/>
  <Item Name="FileOut" ClassName="EnsLib.File.PassthroughOperation" PoolSize="1" Enabled="true">
    <Setting Target="Adapter" Name="FilePath">/tmp</Setting>
  </Item>
</Production>
}

}
